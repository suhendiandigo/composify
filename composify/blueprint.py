"""This module contains implementation for Blueprint."""

import itertools
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Generic, TypeAlias, TypeVar

from composify._qualifiers import Resolution
from composify.constructor import Constructor, ConstructorFunction
from composify.errors import (
    CyclicDependencyError,
    InvalidResolutionModeError,
    MultipleDependencyResolutionError,
    NoConstructorError,
    ResolutionFailureError,
    ResolverError,
)
from composify.metadata.qualifiers import collect_qualifiers
from composify.provider import ConstructorProvider
from composify.resolutions import (
    DEFAULT_RESOLUTION_MODE,
    ResolutionMode,
    ResolutionType,
    is_resolution_mode,
    split_resolution,
)
from composify.types import AnnotatedType

T = TypeVar("T")


__all__ = [
    "Blueprint",
    "BlueprintResolver",
]


@dataclass(frozen=True)
class Blueprint(Generic[T]):
    """Similar to Constructor but contains another Blueprint as the dependencies."""

    source: str = field(hash=False, compare=False)
    constructor: ConstructorFunction[T]
    is_async: bool = field(hash=False, compare=False)
    output_type: AnnotatedType[T] = field(hash=False, compare=False)
    dependencies: frozenset[tuple[str, "Blueprint"]]
    priority: tuple[int, ...] = field(hash=False, compare=False)
    is_optional: bool = field(hash=False, compare=False)


_Parameter: TypeAlias = tuple[str, Blueprint]
_Parameters: TypeAlias = Sequence[_Parameter]


def _permutate_parameters(
    level: int,
    parameters: tuple[_Parameter, ...],
    rest_of_parameters: tuple[tuple[str, tuple[Blueprint, ...]], ...],
):
    if not rest_of_parameters:
        yield parameters, level
    else:
        name, values = rest_of_parameters[0]
        rest_of_parameters = rest_of_parameters[1:]
        for value in values:
            p = parameters + ((name, value),)
            yield from _permutate_parameters(level + 1, p, rest_of_parameters)


def permutate_parameters(
    parameters: Iterable[tuple[str, tuple[Blueprint, ...]]],
) -> tuple[tuple[_Parameters, int], ...]:
    return _permutate_parameters(0, (), tuple(parameters))


ConstructorName: TypeAlias = str
ConstructorResultName: TypeAlias = str


@dataclass(frozen=True)
class _Tracing:
    traces: tuple[tuple[ConstructorName, ConstructorResultName, type], ...]

    def chain(
        self, trace: tuple[ConstructorName, ConstructorResultName, type]
    ) -> "_Tracing":
        return _Tracing(traces=(*self.traces, trace))


def _get_first(iterable):
    return next(iter(iterable), None)


class BlueprintResolver:
    """The main responsibility of this class is to generate all possible
    blueprints from supplied factories.
    """

    def __init__(
        self,
        providers: Iterable[ConstructorProvider],
        default_resolution: ResolutionMode = DEFAULT_RESOLUTION_MODE,
    ) -> None:
        self._providers = tuple(providers)
        self._memo: dict[type, tuple[Constructor, ...]] = {}
        self._default_resolution = default_resolution

    def clear_memo(self) -> None:
        """Clear blueprint memo."""
        self._memo.clear()

    def register_provider(self, provider: ConstructorProvider) -> None:
        """Register a new provider to the resolver.

        Args:
            provider (ConstructorProvider): The provider to register.

        Raises:
            ValueError: If a provider is already register.
        """
        if provider in self._providers:
            raise ValueError(f"Provider {provider!r} is already registered.")
        self._providers = self._providers + (provider,)

        # Our memo is no longer valid
        self.clear_memo()

    def register_providers(
        self, providers: Iterable[ConstructorProvider]
    ) -> None:
        """Register new providers to the resolver.

        Args:
            providers (Iterable[ConstructorProvider]): The providers to register.

        Raises:
            ValueError: If a provider is already register.
        """
        for provider in providers:
            if provider in self._providers:
                raise ValueError(
                    f"Provider {provider!r} is already registered."
                )
            self._providers = self._providers + (provider,)

        # Our memo is no longer valid
        self.clear_memo()

    def _raw_create_plans(
        self, target: AnnotatedType[T]
    ) -> Iterable[Constructor]:
        for provider in self._providers:
            yield from provider.provide_for_type(target)

    def _create_plans(
        self, target: AnnotatedType[T], mode: ResolutionMode
    ) -> tuple[Constructor, ...]:
        result = self._memo.get(target, None)
        if result is None:
            result = tuple(self._raw_create_plans(target))

            self._memo[target] = result
        return result

    def _resolve_unique(
        self,
        target: AnnotatedType[T],
        name: str,
        mode: ResolutionMode,
        trace: _Tracing,
        priority: tuple[int, ...],
    ):
        resolved: Iterable = tuple(
            self._resolve_exhaustive(
                target=target,
                name=name,
                mode=mode,
                trace=trace,
                priority=priority,
            )
        )
        non_optional_count = sum(
            (0 if bp.is_optional else 1) for bp in resolved
        )
        if non_optional_count > 1:
            raise MultipleDependencyResolutionError(
                target,
                tuple(blueprint.source for blueprint in resolved),
                trace.traces,
            )
        for bp in resolved:
            yield bp
            if not bp.is_optional:
                return

    def _resolve_first(
        self,
        target: AnnotatedType[T],
        name: str,
        mode: ResolutionMode,
        trace: _Tracing,
        priority: tuple[int, ...],
    ):
        resolved: Iterable = tuple(
            self._resolve_exhaustive(
                target=target,
                name=name,
                mode=mode,
                trace=trace,
                priority=priority,
            )
        )
        for bp in resolved:
            yield bp
            if not bp.is_optional:
                return

    def _resolve_exhaustive(
        self,
        target: AnnotatedType[T],
        name: str,
        mode: ResolutionMode,
        trace: _Tracing,
        priority: tuple[int, ...],
    ) -> Iterable[Blueprint[T]]:
        plans = self._create_plans(target, mode)
        if not plans:
            raise NoConstructorError(target, trace.traces)
        errors: list[ResolverError] = []
        constructions: list[Blueprint[T]] = []
        for plan_order, plan in enumerate(plans):
            try:
                constructions.extend(
                    self._resolve_plan(
                        target=target,
                        name=name,
                        plan=plan,
                        plan_order=plan_order,
                        mode=mode,
                        trace=trace,
                        priority=priority,
                    )
                )
            except (NoConstructorError, CyclicDependencyError) as exc:
                errors.append(exc)
            except ResolutionFailureError as exc:
                errors.extend(exc.errors)
        if not constructions and errors:
            raise ResolutionFailureError(target, trace.traces, errors)
        yield from constructions

    def _resolve_plan(
        self,
        target: AnnotatedType[T],
        name: str,
        plan: Constructor[T],
        plan_order: int,
        mode: ResolutionMode,
        trace: _Tracing,
        priority: tuple[int, ...],
    ) -> Iterable[Blueprint[T]]:
        curr_trace = plan.source, name, target
        tracing = trace.chain(curr_trace)
        if curr_trace in trace.traces:
            raise CyclicDependencyError(target, tracing.traces)
        if plan.dependencies:
            parameters: list[tuple[str, tuple[Blueprint, ...]]] = []
            for dependency_name, dependency in plan.dependencies:
                parameters.append(
                    (
                        dependency_name,
                        tuple(
                            self._resolve(
                                target=dependency,
                                name=dependency_name,
                                mode=mode,
                                trace=tracing,
                                priority=priority,
                            )
                        ),
                    )
                )
            i = 0
            for parameter_permutation, _ in permutate_parameters(parameters):
                yield Blueprint(
                    source=plan.source,
                    constructor=plan.constructor,
                    # Parent is async if any of the dependencies is async
                    is_async=any(
                        (
                            plan.is_async,
                            *(
                                parameter.is_async
                                for _, parameter in parameter_permutation
                            ),
                        )
                    ),
                    output_type=plan.output_type,
                    dependencies=frozenset(parameter_permutation),
                    priority=priority + (plan_order, i),
                    is_optional=plan.is_optional
                    or any(
                        parameter.is_optional
                        for _, parameter in parameter_permutation
                    ),
                )
                i += 1
        else:
            yield Blueprint(
                source=plan.source,
                constructor=plan.constructor,
                is_async=plan.is_async,
                output_type=plan.output_type,
                dependencies=frozenset(),
                priority=priority + (plan_order, 0),
                is_optional=plan.is_optional,
            )

    def _select_resolver(self, mode: ResolutionType):
        match mode:
            case "unique":
                resolve = self._resolve_unique
            case "exhaustive":
                resolve = self._resolve_exhaustive
            case "select_first":
                resolve = self._resolve_first
            case _:
                raise InvalidResolutionModeError(mode)
        return resolve

    def _resolve(
        self,
        target: AnnotatedType[T],
        name: str,
        mode: ResolutionMode,
        trace: _Tracing,
        priority: tuple[int, ...],
    ) -> Iterable[Blueprint[T]]:
        mode, next_modes = split_resolution(mode)
        qualifiers = collect_qualifiers(target)
        type_ = target
        if resolution := qualifiers.get(Resolution):
            mode = resolution.mode
        else:
            type_ = Annotated[type_, Resolution(mode)]  # type: ignore[assignment]
        resolve = self._select_resolver(mode)
        return resolve(
            type_, name=name, mode=next_modes, trace=trace, priority=priority
        )

    def resolve(
        self,
        target: AnnotatedType[T],
        mode: ResolutionMode | None = None,
    ) -> Iterable[Blueprint[T]]:
        """Generate blueprint for a type.

        Args:
            target (type[T]): The type to generate for.
            mode (ResolutionMode | None, optional): The resolution mode. Defaults to select_first.

        Raises:
            InvalidResolutionModeError: Raised if the resolution mode is invalid.
            ResolutionFailureError: Raised if there is no generated blueprint.

        Returns:
            Iterable[Blueprint[T]]: The blueprint for target type.
        """
        mode = mode or self._default_resolution
        if not is_resolution_mode(mode):
            raise InvalidResolutionModeError(mode)
        tracing = _Tracing(())
        try:
            return sorted(
                self._resolve(
                    target=target,
                    name="__root__",
                    mode=mode,
                    trace=tracing,
                    priority=(),
                ),
                key=lambda x: x.priority,
            )
        except (
            NoConstructorError,
            CyclicDependencyError,
            MultipleDependencyResolutionError,
        ) as exc:
            raise ResolutionFailureError(target, tracing.traces, [exc]) from exc


def _group_key(level: int):
    slice_end = level + 1

    def key(bp: Blueprint):
        return bp.priority[:slice_end]

    return key


class BlueprintGrouper(Generic[T]):
    def __init__(
        self, blueprints: Iterable[Blueprint[T]], level: int | None = 0
    ):
        self._blueprints = tuple(blueprints)
        self._key = _group_key(level) if level is not None else None

    def __iter__(self):
        if self._key is None:
            for bp in self._blueprints:
                yield (bp,)
        else:
            for _, group in itertools.groupby(self._blueprints, key=self._key):
                yield group
