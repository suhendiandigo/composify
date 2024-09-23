from dataclasses import dataclass, field
from typing import Generic, Iterable, TypeAlias, TypeVar

from declarative_app.constructor import Constructor, ConstructorFunction
from declarative_app.provider import ConstructorProvider

T = TypeVar("T")


__all__ = [
    "Blueprint",
    "BlueprintResolver",
    "ResolverError",
    "TypeConstructionResolutionError",
    "TracedTypeConstructionResolutionError",
    "NoConstructorError",
    "CyclicDependencyError",
    "FailedToResolveError",
]


class ResolverError(Exception):
    pass


class TypeConstructionResolutionError(ResolverError):

    def __init__(self, type_: type, msg: str) -> None:
        super().__init__(msg)
        self.type_ = type_


Trace: TypeAlias = tuple[str, str, type]
Traces: TypeAlias = tuple[Trace, ...]


class TracedTypeConstructionResolutionError(TypeConstructionResolutionError):

    def __init__(self, type_: type, traces: Traces, msg: str) -> None:
        super().__init__(type_, msg)
        self.traces = traces


class NoConstructorError(TracedTypeConstructionResolutionError):
    def __init__(self, type_: type, traces: Traces) -> None:
        super().__init__(
            type_, traces, f"Unable to find constructor for {type_!r}"
        )


class CyclicDependencyError(TracedTypeConstructionResolutionError):
    def __init__(self, type_: type, traces: Traces) -> None:
        super().__init__(
            type_, traces, f"Cyclic dependency found for {type_!r}"
        )


class FailedToResolveError(TracedTypeConstructionResolutionError):
    def __init__(
        self,
        type_: type,
        traces: Traces,
        errors: Iterable[TracedTypeConstructionResolutionError],
    ) -> None:
        self.errors = errors
        super().__init__(
            type_,
            traces,
            f"Failed to resolve for {type_!r}",
        )


@dataclass(frozen=True)
class Blueprint(Generic[T]):
    """Similar to Constructor but contains another Blueprint as the dependencies."""

    source: str = field(hash=False)
    constructor: ConstructorFunction[T]
    is_async: bool = field(hash=False)
    output_type: type[T] = field(hash=False)
    dependencies: tuple[tuple[str, "Blueprint"], ...]
    chain_length: int = field(hash=False)


_Parameter: TypeAlias = tuple[str, Blueprint]
_Parameters: TypeAlias = tuple[_Parameter, ...]


def _permutate_parameters(
    level: int,
    parameters: _Parameters,
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
    parameters: dict[str, tuple[Blueprint, ...]]
) -> tuple[tuple[_Parameters, int], ...]:
    values = tuple(parameters.items())
    return _permutate_parameters(0, tuple(), values)


ConstructorName: TypeAlias = str
ConstructorResultName: TypeAlias = str


@dataclass(frozen=True)
class Tracing:
    traces: tuple[tuple[ConstructorName, ConstructorResultName, type], ...]

    def chain(
        self, trace: tuple[ConstructorName, ConstructorResultName, type]
    ) -> "Tracing":
        return Tracing(traces=(*self.traces, trace))


class BlueprintResolver:
    """The main responsibility of this class is to generate all possible
    blueprints from supplied factories.
    """

    def __init__(
        self,
        factories: Iterable[ConstructorProvider],
        is_exhaustive: bool = False,
    ) -> None:
        self._factories = tuple(factories)
        self._is_exhaustive = is_exhaustive
        self._memo: dict[type, tuple[Constructor, ...]] = {}

    def _raw_create_plans(self, target: type[T]) -> Iterable[Constructor]:
        for factory in self._factories:
            yield from factory.provide_for_type(target)

    def _create_plans(self, target: type[T]) -> tuple[Constructor, ...]:
        result = self._memo.get(target, None)
        if result is None:
            result = self._memo[target] = tuple(self._raw_create_plans(target))
        return result

    def _resolve_plan(
        self,
        target: type[T],
        name: str,
        plan: Constructor[T],
        trace: Tracing,
    ) -> Iterable[Blueprint[T]]:
        curr_trace = plan.source, name, target
        tracing = trace.chain(curr_trace)
        if curr_trace in trace.traces:
            raise CyclicDependencyError(target, tracing.traces)
        if plan.dependencies:
            parameters: dict[str, tuple[Blueprint, ...]] = {}
            for dependency_name, dependency in plan.dependencies:
                parameters[dependency_name] = tuple(
                    self._resolve(dependency, dependency_name, tracing)
                )
            for parameter_permutation, level in permutate_parameters(
                parameters
            ):
                yield Blueprint(
                    source=plan.source,
                    constructor=plan.constructor,
                    is_async=plan.is_async,
                    output_type=plan.output_type,
                    dependencies=parameter_permutation,
                    chain_length=level,
                )
        else:
            yield Blueprint(
                source=plan.source,
                constructor=plan.constructor,
                is_async=plan.is_async,
                output_type=plan.output_type,
                dependencies=tuple(),
                chain_length=0,
            )

    def _resolve(
        self, target: type[T], name: str, trace: Tracing
    ) -> Iterable[Blueprint[T]]:
        plans = self._create_plans(target)
        if not plans:
            raise NoConstructorError(target, trace.traces)
        errors: list[TracedTypeConstructionResolutionError] = []
        constructions: list[Blueprint[T]] = []
        for plan in plans:
            try:
                constructions.extend(
                    self._resolve_plan(target, name, plan, trace)
                )
            except (NoConstructorError, CyclicDependencyError) as exc:
                errors.append(exc)
            except FailedToResolveError as exc:
                errors.extend(exc.errors)
        if not constructions and errors:
            raise FailedToResolveError(target, trace.traces, errors)
        yield from constructions

    def resolve(self, target: type[T]) -> Iterable[Blueprint[T]]:
        tracing = Tracing(tuple())
        try:
            return sorted(
                self._resolve(target, "__root__", tracing),
                key=lambda x: x.chain_length,
            )
        except (NoConstructorError, CyclicDependencyError) as exc:
            raise FailedToResolveError(target, tracing.traces, [exc])
