from dataclasses import dataclass
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Iterable,
    Mapping,
    ParamSpec,
    Protocol,
    TypeAlias,
    TypeVar,
)

from declarative_app.container import Container
from declarative_app.errors import (
    FailedToResolveError,
    InstanceNotFoundError,
    NoConstructPlanError,
)
from declarative_app.rules import RuleRegistry

T = TypeVar("T")
P = ParamSpec("P")


@dataclass(frozen=True)
class Static(Generic[T]):
    value: T

    def __call__(self) -> Any:
        return self.value


Constructor: TypeAlias = Callable[..., Awaitable[T]] | Callable[..., T]


@dataclass(frozen=True)
class ConstructionPlan(Generic[T]):
    name: str
    constructor: Constructor[T]
    is_async: bool
    dependencies: Mapping[str, type]


@dataclass(frozen=True)
class Construction(Generic[T]):
    name: str
    constructor: Constructor[T]
    is_async: bool
    parameters: Mapping[str, "Construction"]
    chain_length: int


ConstructorName: TypeAlias = str
ConstructorResultName: TypeAlias = str


@dataclass(frozen=True)
class Tracing:
    traces: tuple[tuple[ConstructorName, ConstructorResultName, type], ...]

    def chain(
        self,
        resolver_name: ConstructorName,
        dependency: ConstructorResultName,
        dependency_type: type,
    ) -> "Tracing":
        return Tracing(
            traces=(*self.traces, (resolver_name, dependency, dependency_type))
        )


class ConstructionPlanFactory(Protocol):

    def create_plan(self, type_: type[T]) -> Iterable[ConstructionPlan[T]]:
        raise NotImplementedError()


class ContainerConstructionPlanFactory(ConstructionPlanFactory):

    __slots__ = "_container"

    def __init__(
        self,
        container: Container,
    ) -> None:
        self._container = container

    @property
    def container(self) -> Container:
        return self._container

    def create_plan(self, type_: type[T]) -> Iterable[ConstructionPlan[T]]:
        try:
            val = self._container.get(type_)
            yield ConstructionPlan(
                name=f"{self._container}::resolver",
                constructor=Static(val),
                is_async=False,
                dependencies={},
            )
        except InstanceNotFoundError:
            pass


class ConstructRuleConstructionPlanFactory(ConstructionPlanFactory):

    __slots__ = "_rules"

    _rules: RuleRegistry

    def __init__(self, rules: RuleRegistry) -> None:
        self._rules = rules

    def create_plan(self, type_: type[T]) -> Iterable[ConstructionPlan[T]]:
        rules = self._rules.get(type_)
        if not rules:
            return
        errors = []
        for rule in rules:
            try:
                yield ConstructionPlan(
                    name=f"rule::{rule.cannonical_name}",
                    constructor=rule.function,
                    is_async=rule.is_async,
                    dependencies=rule.parameter_types,
                )
            except NoConstructPlanError as exc:
                errors.append(exc)


def _permutate_parameters(
    level: int,
    parameters: dict[str, Construction],
    rest_of_parameters: tuple[tuple[str, tuple[Construction, ...]], ...],
):
    if not rest_of_parameters:
        yield parameters, level
    else:
        name, values = rest_of_parameters[0]
        rest_of_parameters = rest_of_parameters[1:]
        for value in values:
            p = parameters.copy()
            p[name] = value
            yield from _permutate_parameters(level + 1, p, rest_of_parameters)


def permutate_parameters(
    parameters: dict[str, tuple[Construction, ...]]
) -> tuple[tuple[dict[str, Construction], int], ...]:
    values = tuple(parameters.items())
    return _permutate_parameters(0, {}, values)


class ConstructionResolver:

    def __init__(self, factories: Iterable[ConstructionPlanFactory]) -> None:
        self._factories = tuple(factories)

    def _resolve(
        self, target: type[T], name: str, trace: Tracing
    ) -> Iterable[Construction[T]]:
        plans: list[ConstructionPlan] = []
        for factory in self._factories:
            plans.extend(factory.create_plan(target))
        if plans is None:
            raise FailedToResolveError(target, trace)
        for plan in plans:
            tracing = trace.chain(plan.name, name, target)
            if plan.dependencies:
                parameters: dict[str, tuple[Construction, ...]] = {}
                for dependency_name, dependency in plan.dependencies.items():
                    parameters[dependency_name] = tuple(
                        self._resolve(dependency, dependency_name, tracing)
                    )
                for parameter_permutation, level in permutate_parameters(
                    parameters
                ):
                    yield Construction(
                        name=plan.name,
                        constructor=plan.constructor,
                        is_async=plan.is_async,
                        parameters=parameter_permutation,
                        chain_length=level,
                    )
            else:
                yield Construction(
                    name=plan.name,
                    constructor=plan.constructor,
                    is_async=plan.is_async,
                    parameters={},
                    chain_length=0,
                )

    def resolve(self, target: type[T]) -> Iterable[Construction[T]]:
        tracing = Tracing(tuple())
        return sorted(
            self._resolve(target, "__root__", tracing),
            key=lambda x: x.chain_length,
        )


async def construct(construction: Construction[T]) -> T:
    parameters = {
        name: await construct(param)
        for name, param in construction.parameters.items()
    }
    if construction.is_async:
        return await construction.constructor(**parameters)  # type: ignore[misc]
    else:
        return construction.constructor(**parameters)  # type: ignore[return-value]
