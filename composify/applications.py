"""Main Composify implementation."""

import asyncio
import itertools
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Any, TypeVar

from composify.blueprint import (
    DEFAULT_RESOLUTION_MODE,
    Blueprint,
    BlueprintGrouper,
    BlueprintResolver,
)
from composify.builder import AsyncBuilder, Builder
from composify.container import Container, ContainerGetter
from composify.errors import (
    MultipleResolutionError,
    NoConstructorError,
    NoResolutionError,
    NoValueError,
    ResolutionFailureError,
)
from composify.get import Get
from composify.get_or_create import (
    AsyncGetOrCreate,
    GetOrCreate,
    ResolutionMode,
)
from composify.injector import AsyncInjector, Injector
from composify.provider import (
    ConstructorProvider,
    ContainerInstanceProvider,
    RuleBasedConstructorProvider,
)
from composify.resolutions import EXHAUSTIVE, join_resolution
from composify.rules import ConstructRule, RuleRegistry, as_rule
from composify.types import AnnotatedType

T = TypeVar("T")


def _ensure_rule_type(rule: ConstructRule | Callable) -> ConstructRule:
    r = as_rule(rule)
    if r is None:
        raise TypeError(
            f"{rule!r} of type{type(rule)!r} is not a rule. To declare a rule, use the @rule decorator."
        )
    return r


def _skip_no_constructor_error(
    exc: ResolutionFailureError,
) -> ResolutionFailureError | None:
    errors = tuple(
        error
        for error in exc.errors
        if not isinstance(error, NoConstructorError)
    )
    if errors:
        return ResolutionFailureError(exc.type_, exc.traces, errors)
    return None


def _select_blueprint(type_: AnnotatedType[T], plans: tuple[Blueprint[T], ...]):
    selected = []
    is_non_optional_selected = False
    for plan in plans:
        if plan.is_optional:
            if not is_non_optional_selected:
                selected.append(plan)
        elif is_non_optional_selected:
            raise MultipleResolutionError(type_, plans)
        else:
            is_non_optional_selected = True
            selected.append(plan)
    if len(selected) == 0:
        raise NoResolutionError(type_)
    return selected


def _is_not_none(val: Any) -> bool:
    return val is not None


def _skip_no_value_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NoValueError:
            return None

    return wrapper


def _async_skip_no_value_error(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except NoValueError:
            return None

    return wrapper


class ComposifyGetOrCreate(GetOrCreate):
    """Synchronous Get or Create protocol implementation using Composify. Only support non async @rule."""

    def __init__(
        self,
        resolver: BlueprintResolver,
        builder: Builder,
        default_resolution: ResolutionMode,
    ) -> None:
        super().__init__(default_resolution)
        self._resolver = resolver
        self._builder = builder

    def one(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> T:
        """Get one instance of T.

        Args:
            type_ (AnnotatedType[T]): The type to get.
            resolution_mode (ResolutionMode | None, optional): How the dependency graph is resolved. Defaults to select_first.

        Returns:
            T: An instance of T

        Raises:
            InvalidResolutionModeError: Raised if the resolution mode is invalid.
            MultipleResolutionError: If there are multiple possible instances.
            NoResolutionError: If there is no available instance.
        """
        plans = _select_blueprint(
            type_,
            tuple(
                self._resolver.resolve(type_, self._resolution(resolution_mode))
            ),
        )
        return self._create_one_in_group(type_, plans)

    def all(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> Sequence[T]:
        """Get all instance of T.

        Args:
            type_ (AnnotatedType[T]): The type to get.
            resolution_mode (ResolutionMode | None, optional): How the dependency graph is resolved. Defaults to select_first.

        Returns:
            Sequence[T]: All instances of T.

        Raises:
            InvalidResolutionModeError: Raised if the resolution mode is invalid.
        """
        resolution_mode = self._resolution(resolution_mode)
        try:
            plans = tuple(  # type: ignore[var-annotated]
                self._resolver.resolve(
                    type_, join_resolution(EXHAUSTIVE, resolution_mode)
                )
            )
        except ResolutionFailureError as exc:
            new_exc = _skip_no_constructor_error(exc)
            if new_exc:
                raise new_exc from exc
            return ()
        return tuple(
            filter(
                _is_not_none,
                (
                    self._create_one_in_group(type_, tuple(group))
                    for group in BlueprintGrouper(plans)
                ),
            )
        )

    def _create_one_in_group(
        self, type_: AnnotatedType[T], plans: Iterable[Blueprint[T]]
    ) -> T:
        result = None
        for plan in plans:
            try:
                result = self._builder.from_blueprint(plan)
                if result is not None:
                    break
            except NoValueError:
                pass
        if result is None:
            raise NoValueError(type_)
        return result


class ComposifyAsyncGetOrCreate(AsyncGetOrCreate):
    """Asynchronous Get or Create protocol implementation using Composify."""

    def __init__(
        self,
        resolver: BlueprintResolver,
        builder: AsyncBuilder,
        default_resolution: ResolutionMode,
    ) -> None:
        super().__init__(default_resolution)
        self._resolver = resolver
        self._builder = builder

    async def one(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> T:
        """Get one instance of T.

        Args:
            type_ (AnnotatedType[T]): The type to get.
            resolution_mode (ResolutionMode | None, optional): How the dependency graph is resolved. Defaults to select_first.

        Returns:
            T: An instance of T

        Raises:
            InvalidResolutionModeError: Raised if the resolution mode is invalid.
            MultipleResolutionError: If there are multiple possible instances.
            NoResolutionError: If there is no available instance.
        """
        plans = _select_blueprint(
            type_,
            tuple(
                self._resolver.resolve(type_, self._resolution(resolution_mode))
            ),
        )
        return await self._create_one_in_group(type_, plans)

    async def all(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> Sequence[T]:
        """Get all instance of T.

        Args:
            type_ (AnnotatedType[T]): The type to get.
            resolution_mode (ResolutionMode | None, optional): How the dependency graph is resolved. Defaults to select_first.

        Returns:
            Sequence[T]: All instances of T.

        Raises:
            InvalidResolutionModeError: Raised if the resolution mode is invalid.
        """
        resolution_mode = self._resolution(resolution_mode)
        try:
            plans = tuple(  # type: ignore[var-annotated]
                self._resolver.resolve(
                    type_, join_resolution(EXHAUSTIVE, resolution_mode)
                )
            )
        except ResolutionFailureError as exc:
            new_exc = _skip_no_constructor_error(exc)
            if new_exc:
                raise new_exc from exc
            return ()
        return tuple(
            filter(
                _is_not_none,
                await asyncio.gather(
                    *(
                        self._create_one_in_group(type_, tuple(group))
                        for group in BlueprintGrouper(plans)
                    )
                ),
            )
        )

    async def _create_one_in_group(
        self, type_: AnnotatedType[T], plans: Blueprint[T]
    ) -> T | None:
        result = None
        for plan in plans:
            try:
                result = await self._builder.from_blueprint(plan)
                if result is not None:
                    break
            except NoValueError:
                pass
        if result is None:
            raise NoValueError(type_)
        return result


class BaseComposify:
    """Minimalist Composify app class. The main entry point to use Composify.

    Example:
        from composify import BaseComposify

        composify = BaseComposify()

    """

    def __init__(
        self,
        initial: Iterable[Any] = (),
        *,
        name: str | None = None,
        allows_async: bool,
        rules: Iterable[ConstructRule] = (),
        providers: Iterable[ConstructorProvider] = (),
        default_resolution: ResolutionMode = DEFAULT_RESOLUTION_MODE,
    ) -> None:
        # Core components
        self._default_resolution = default_resolution
        self._container = Container(name)
        self._rules = RuleRegistry(allows_async=allows_async)
        self._resolver = BlueprintResolver(
            [
                ContainerInstanceProvider(self._container),
                RuleBasedConstructorProvider(self._rules),
            ],
            default_resolution=default_resolution,
        )
        self._getter = ContainerGetter(self._container)
        self._container.add(self)
        self._container.add(self._container)
        self._container.add(self._getter)

        for value in initial:
            self._container.add(value)

        # Register user providers and rules
        if providers is not None:
            self._resolver.register_providers(providers)
        if rules is not None:
            self._rules.register_rules(rules)

    @property
    def container(self) -> Container:
        """The container of this composify object."""
        return self._container

    @property
    def default_resolution(self) -> ResolutionMode:
        """The default resolution mode."""
        return self._default_resolution

    @property
    def add(self):
        """Add a new object to the container."""
        return self._container.add

    @property
    def remove(self):
        """Add a new object to the container."""
        return self._container.remove

    @property
    def get(self) -> Get:
        """Get a an existing component."""
        return self._getter

    def add_rule(self, rule: ConstructRule | Callable) -> None:
        """Register a new rule."""
        self._rules.register_rule(_ensure_rule_type(rule))
        self._resolver.clear_memo()

    def add_rules(self, *rules: Iterable[ConstructRule]) -> None:
        """Register multiple new rules."""
        self._rules.register_rules(
            r
            for rule in itertools.chain.from_iterable(rules)
            if (r := _ensure_rule_type(rule))
        )
        self._resolver.clear_memo()

    def register_provider(self, provider: ConstructorProvider) -> None:
        """Register a new provider."""
        self._resolver.register_provider(provider)

    def register_providers(self, *providers: ConstructorProvider) -> None:
        """Register multiple new providers."""
        self._resolver.register_providers(providers)


class _SyncMixin(BaseComposify):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Supports for simple get_or_create and auto-wiring via inject.
        self._builder = Builder(save_to=self._container)
        self._get_or_create = ComposifyGetOrCreate(
            self._resolver, self._builder, self.default_resolution
        )
        self._injector = Injector(self._get_or_create)

        self._container.add(self._get_or_create)
        self._container.add(self._injector)

    @property
    def inject(self) -> Injector:
        """Injector instance."""
        return self._injector

    @property
    def get_or_create(self) -> GetOrCreate:
        """Get or Create a new component."""
        return self._get_or_create


class _AsyncMixin(BaseComposify):
    def __init__(
        self,
        *args,
        threadpool_executor: ThreadPoolExecutor | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        # Supports for async aget_or_create and async auto-wiring via ainject.
        self._async_builder = AsyncBuilder(
            save_to=self._container, threadpool_executor=threadpool_executor
        )
        self._async_get_or_create = ComposifyAsyncGetOrCreate(
            self._resolver, self._async_builder, self.default_resolution
        )
        self._async_injector = AsyncInjector(self._async_get_or_create)

        self._container.add(self._async_get_or_create)
        self._container.add(self._async_injector)

    @property
    def ainject(self) -> AsyncInjector:
        """Async injector instance."""
        return self._async_injector

    @property
    def aget_or_create(self) -> AsyncGetOrCreate:
        """Get or Create a new component."""
        return self._async_get_or_create


class Composify(_SyncMixin):
    """Composify app class. The main entry point to use Composify.

    Example:
        composify = Composify()

    """

    def __init__(
        self,
        initial: Iterable[Any] = (),
        *,
        name: str | None = None,
        rules: Iterable[ConstructRule] = (),
        providers: Iterable[ConstructorProvider] = (),
        default_resolution: ResolutionMode = DEFAULT_RESOLUTION_MODE,
    ) -> None:
        super().__init__(
            initial,
            name=name,
            rules=rules,
            providers=providers,
            default_resolution=default_resolution,
            allows_async=False,
        )


class AsyncComposify(_SyncMixin, _AsyncMixin):
    """Composify app class for asyncio support. The main entry point to use Composify.
    By default, sync @rule are called directly without threadpool executor.
    To configure Composify to use threadpool, simply include a threadpool_executor parameter.

    Example:
        from concurrent.futures import ThreadPoolExecutor

        from composify import AsyncComposify

        composify = AsyncComposify(
            threadpool_executor=ThreadPoolExecutor()
        )

    """

    def __init__(
        self,
        initial: Iterable[Any] = (),
        *,
        name: str | None = None,
        rules: Iterable[ConstructRule] | None = None,
        providers: Iterable[ConstructorProvider] | None = None,
        default_resolution: ResolutionMode = DEFAULT_RESOLUTION_MODE,
        threadpool_executor: ThreadPoolExecutor | None = None,
    ) -> None:
        super().__init__(
            initial,
            name=name,
            rules=rules,
            providers=providers,
            default_resolution=default_resolution,
            threadpool_executor=threadpool_executor,
            allows_async=True,
        )
