import asyncio
import itertools
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import TypeVar

from composify.blueprint import DEFAULT_RESOLUTION_MODE, BlueprintResolver
from composify.builder import AsyncBuilder, Builder
from composify.container import Container, ContainerGetter
from composify.errors import NoConstructorError, ResolutionFailureError
from composify.get_or_create import (
    AsyncGetOrCreate,
    GetOrCreate,
    ResolutionMode,
    select_blueprint,
)
from composify.injector import Injector
from composify.provider import (
    ConstructorProvider,
    ContainerInstanceProvider,
    RuleBasedConstructorProvider,
)
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


class ComposifyGetOrCreate(GetOrCreate):
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
        plans = tuple(
            self._resolver.resolve(type_, self._resolution(resolution_mode))
        )
        plan = select_blueprint(type_, plans)
        return self._builder.from_blueprint(plan)

    def all(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> Sequence[T]:
        try:
            plans = tuple(
                self._resolver.resolve(type_, self._resolution(resolution_mode))
            )
        except ResolutionFailureError as exc:
            new_exc = _skip_no_constructor_error(exc)
            if new_exc:
                raise new_exc from exc
            return ()
        return tuple(self._builder.from_blueprint(plan) for plan in plans)


class ComposifyAsyncGetOrCreate(AsyncGetOrCreate):
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
        plans = tuple(
            self._resolver.resolve(type_, self._resolution(resolution_mode))
        )
        plan = select_blueprint(type_, plans)
        return await self._builder.from_blueprint(plan)

    async def all(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> Sequence[T]:
        try:
            plans = tuple(
                self._resolver.resolve(type_, self._resolution(resolution_mode))
            )
        except ResolutionFailureError as exc:
            new_exc = _skip_no_constructor_error(exc)
            if new_exc:
                raise new_exc from exc
            return ()
        return tuple(
            await asyncio.gather(
                *(self._builder.from_blueprint(plan) for plan in plans)
            )
        )


class Composify:
    def __init__(
        self,
        name: str | None = None,
        *,
        rules: Iterable[ConstructRule] | None = None,
        providers: Iterable[ConstructorProvider] | None = None,
        default_resolution: ResolutionMode = DEFAULT_RESOLUTION_MODE,
    ) -> None:
        self._default_resolution = default_resolution
        self._container = Container(name)
        self._rules = RuleRegistry()
        self._resolver = BlueprintResolver(
            [
                ContainerInstanceProvider(self._container),
                RuleBasedConstructorProvider(self._rules),
            ]
        )
        self._async_builder = AsyncBuilder(save_to=self._container)
        self._builder = Builder(save_to=self._container)
        self._getter = ContainerGetter(self._container)
        self._injector = Injector(self._getter)
        self._get_or_create = ComposifyGetOrCreate(
            self._resolver, self._builder, default_resolution
        )
        self._async_get_or_create = ComposifyAsyncGetOrCreate(
            self._resolver, self._async_builder, default_resolution
        )

        self._container.add(self)
        self._container.add(self._container)
        self._container.add(self._getter)
        self._container.add(self._get_or_create)
        self._container.add(self._async_get_or_create)
        self._container.add(self._injector)

        if providers is not None:
            self._resolver.register_providers(providers)
        if rules is not None:
            self._rules.register_rules(rules)

    @property
    def container(self) -> Container:
        return self._container

    @property
    def inject(self) -> Injector:
        return self._injector

    @property
    def default_resolution(self) -> ResolutionMode:
        return self._default_resolution

    @property
    def add(self):
        return self._container.add

    def add_rule(self, rule: ConstructRule | Callable) -> None:
        self._rules.register_rule(_ensure_rule_type(rule))
        self._resolver.clear_memo()

    def add_rules(self, *rules: Iterable[ConstructRule]) -> None:
        self._rules.register_rules(
            r
            for rule in itertools.chain.from_iterable(rules)
            if (r := _ensure_rule_type(rule))
        )
        self._resolver.clear_memo()

    def register_provider(self, provider: ConstructorProvider) -> None:
        self._resolver.register_provider(provider)

    def register_providers(self, *providers: ConstructorProvider) -> None:
        self._resolver.register_providers(providers)

    def aget_or_create(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> Awaitable[T]:
        return self._async_get_or_create.one(type_, resolution_mode)

    def aget_or_create_all(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> Awaitable[Sequence[T]]:
        return self._async_get_or_create.all(type_, resolution_mode)

    def get_or_create(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> T:
        return self._get_or_create.one(type_, resolution_mode)

    def get_or_create_all(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> Sequence[T]:
        return self._get_or_create.all(type_, resolution_mode)
