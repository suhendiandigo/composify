from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Annotated, Generic, TypeAlias, TypeVar

from composify.constructor import Constructor, ConstructorFunction
from composify.errors import (
    CyclicDependencyError,
    NoConstructorError,
    ResolutionFailureError,
)
from composify.metadata.attributes import ProvidedBy
from composify.provider import ConstructorProvider
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


_Parameter: TypeAlias = tuple[str, Blueprint]
_Parameters: TypeAlias = frozenset[_Parameter]


def _permutate_parameters(
    level: int,
    parameters: tuple[_Parameter, ...],
    rest_of_parameters: tuple[tuple[str, tuple[Blueprint, ...]], ...],
):
    if not rest_of_parameters:
        yield frozenset(parameters), level
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
        providers: Iterable[ConstructorProvider],
    ) -> None:
        self._providers = tuple(providers)
        self._memo: dict[type, tuple[Constructor, ...]] = {}

    def clear_memo(self) -> None:
        self._memo.clear()

    def register_provider(self, provider: ConstructorProvider) -> None:
        """Register a new provider to the resolver."""
        if provider in self._providers:
            raise ValueError(f"Provider {provider!r} is already registered.")
        self._providers = self._providers + (provider,)

        # Our memo is no longer valid
        self.clear_memo()

    def _raw_create_plans(
        self, target: AnnotatedType[T]
    ) -> Iterable[Constructor]:
        for provider in self._providers:
            yield from provider.provide_for_type(target)

    def _create_plans(
        self, target: AnnotatedType[T]
    ) -> tuple[Constructor, ...]:
        result = self._memo.get(target, None)
        if result is None:
            result = self._memo[target] = tuple(self._raw_create_plans(target))
        return result

    def _resolve_plan(
        self,
        target: AnnotatedType[T],
        name: str,
        plan: Constructor[T],
        plan_order: int,
        trace: Tracing,
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
                            self._resolve(dependency, dependency_name, tracing)
                        ),
                    )
                )
            i = 0
            for parameter_permutation, level in permutate_parameters(
                parameters
            ):
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
                    output_type=Annotated[
                        plan.output_type, ProvidedBy(plan.source)
                    ],
                    dependencies=parameter_permutation,
                    priority=(level, plan_order, i),
                )
                i += 1
        else:
            yield Blueprint(
                source=plan.source,
                constructor=plan.constructor,
                is_async=plan.is_async,
                output_type=Annotated[
                    plan.output_type, ProvidedBy(plan.source)
                ],
                dependencies=frozenset(),
                priority=(0, plan_order),
            )

    def _resolve(
        self, target: type[T], name: str, trace: Tracing
    ) -> Iterable[Blueprint[T]]:
        plans = self._create_plans(target)
        if not plans:
            raise NoConstructorError(target, trace.traces)
        errors: list[Exception] = []
        constructions: list[Blueprint[T]] = []
        for plan_order, plan in enumerate(plans):
            try:
                constructions.extend(
                    self._resolve_plan(target, name, plan, plan_order, trace)
                )
            except (NoConstructorError, CyclicDependencyError) as exc:
                errors.append(exc)
            except ResolutionFailureError as exc:
                errors.extend(exc.errors)
        if not constructions and errors:
            raise ResolutionFailureError(target, trace.traces, errors)
        yield from constructions

    def resolve(self, target: type[T]) -> Iterable[Blueprint[T]]:
        tracing = Tracing(())
        try:
            return sorted(
                self._resolve(target, "__root__", tracing),
                key=lambda x: x.priority,
            )
        except (NoConstructorError, CyclicDependencyError) as exc:
            raise ResolutionFailureError(target, tracing.traces, [exc])
