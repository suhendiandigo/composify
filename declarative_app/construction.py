import asyncio
from dataclasses import dataclass, field
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Iterable,
    ParamSpec,
    Protocol,
    TypeAlias,
    TypeVar,
)

from declarative_app.container import Container
from declarative_app.errors import (
    CyclicDependencyError,
    FailedToResolveError,
    InstanceNotFoundError,
    NoConstructPlanError,
    TracedTypeConstructionResolutionError,
)
from declarative_app.rules import ParameterTypes, RuleRegistry

T = TypeVar("T")
P = ParamSpec("P")


@dataclass(frozen=True)
class Static(Generic[T]):
    value: T

    def __call__(self) -> Any:
        return self.value


_ConstructorFunction: TypeAlias = (
    Callable[..., Awaitable[T]] | Callable[..., T]
)


@dataclass(frozen=True)
class ConstructionPlan(Generic[T]):
    source: str
    constructor: _ConstructorFunction[T]
    is_async: bool
    output_type: type[T]
    dependencies: ParameterTypes


@dataclass(frozen=True)
class Construction(Generic[T]):
    source: str = field(hash=False)
    constructor: _ConstructorFunction[T]
    is_async: bool = field(hash=False)
    output_type: type[T] = field(hash=False)
    parameters: tuple[tuple[str, "Construction"], ...]
    chain_length: int = field(hash=False)


ConstructorName: TypeAlias = str
ConstructorResultName: TypeAlias = str


@dataclass(frozen=True)
class Tracing:
    traces: tuple[tuple[ConstructorName, ConstructorResultName, type], ...]

    def chain(
        self, trace: tuple[ConstructorName, ConstructorResultName, type]
    ) -> "Tracing":
        return Tracing(traces=(*self.traces, trace))


class ConstructionPlanFactory(Protocol):

    def create_plan(self, type_: type[T]) -> Iterable[ConstructionPlan[T]]:
        raise NotImplementedError()


class ContainerConstructionPlanFactory(ConstructionPlanFactory):
    __slots__ = ("_container",)

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
            wrapper = self._container.get_wrapper(type_)
            yield ConstructionPlan(
                source=f"{self._container}::{wrapper.name}",
                constructor=Static(wrapper.instance),
                is_async=False,
                output_type=type_,
                dependencies=frozenset(),
            )
        except InstanceNotFoundError:
            pass


class ConstructRuleConstructionPlanFactory(ConstructionPlanFactory):
    __slots__ = ("_rules",)

    _rules: RuleRegistry

    def __init__(self, rules: RuleRegistry) -> None:
        self._rules = rules

    def create_plan(self, type_: type[T]) -> Iterable[ConstructionPlan[T]]:
        rules = self._rules.get(type_)
        if not rules:
            return
        for rule in rules:
            yield ConstructionPlan(
                source=f"rule::{rule.cannonical_name}",
                constructor=rule.function,
                is_async=rule.is_async,
                output_type=type_,
                dependencies=rule.parameter_types,
            )


ParameterConstruction: TypeAlias = tuple[str, Construction]
ParameterConstructions: TypeAlias = tuple[ParameterConstruction, ...]


def _permutate_parameters(
    level: int,
    parameters: ParameterConstructions,
    rest_of_parameters: tuple[tuple[str, tuple[Construction, ...]], ...],
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
    parameters: dict[str, tuple[Construction, ...]]
) -> tuple[tuple[ParameterConstructions, int], ...]:
    values = tuple(parameters.items())
    return _permutate_parameters(0, tuple(), values)


@dataclass(frozen=True)
class ResolutionContext:
    pass


class ConstructionResolver:

    def __init__(
        self,
        factories: Iterable[ConstructionPlanFactory],
        is_exhaustive: bool = False,
    ) -> None:
        self._factories = tuple(factories)
        self._is_exhaustive = is_exhaustive
        self._memo: dict[type, tuple[ConstructionPlan, ...]] = {}

    def _raw_create_plans(self, target: type[T]) -> Iterable[ConstructionPlan]:
        for factory in self._factories:
            yield from factory.create_plan(target)

    def _create_plans(self, target: type[T]) -> tuple[ConstructionPlan, ...]:
        result = self._memo.get(target, None)
        if result is None:
            result = self._memo[target] = tuple(self._raw_create_plans(target))
        return result

    def _resolve_plan(
        self,
        target: type[T],
        name: str,
        plan: ConstructionPlan[T],
        trace: Tracing,
    ) -> Iterable[Construction[T]]:
        curr_trace = plan.source, name, target
        tracing = trace.chain(curr_trace)
        if curr_trace in trace.traces:
            raise CyclicDependencyError(target, tracing.traces)
        if plan.dependencies:
            parameters: dict[str, tuple[Construction, ...]] = {}
            for dependency_name, dependency in plan.dependencies:
                parameters[dependency_name] = tuple(
                    self._resolve(dependency, dependency_name, tracing)
                )
            for parameter_permutation, level in permutate_parameters(
                parameters
            ):
                yield Construction(
                    source=plan.source,
                    constructor=plan.constructor,
                    is_async=plan.is_async,
                    output_type=plan.output_type,
                    parameters=parameter_permutation,
                    chain_length=level,
                )
        else:
            yield Construction(
                source=plan.source,
                constructor=plan.constructor,
                is_async=plan.is_async,
                output_type=plan.output_type,
                parameters=tuple(),
                chain_length=0,
            )

    def _resolve(
        self, target: type[T], name: str, trace: Tracing
    ) -> Iterable[Construction[T]]:
        plans = self._create_plans(target)
        if not plans:
            raise NoConstructPlanError(target, trace.traces)
        errors: list[TracedTypeConstructionResolutionError] = []
        constructions: list[Construction[T]] = []
        for plan in plans:
            try:
                constructions.extend(
                    self._resolve_plan(target, name, plan, trace)
                )
            except (NoConstructPlanError, CyclicDependencyError) as exc:
                errors.append(exc)
            except FailedToResolveError as exc:
                errors.extend(exc.errors)
        if not constructions and errors:
            raise FailedToResolveError(target, trace.traces, errors)
        yield from constructions

    def resolve(self, target: type[T]) -> Iterable[Construction[T]]:
        tracing = Tracing(tuple())
        try:
            return sorted(
                self._resolve(target, "__root__", tracing),
                key=lambda x: x.chain_length,
            )
        except (NoConstructPlanError, CyclicDependencyError) as exc:
            raise FailedToResolveError(target, tracing.traces, [exc])


def _format_construction_string(
    name: str, construction: Construction, indent: int, level: int
) -> str:
    indent_str = " " * (level * indent)
    result = f"{indent_str}{name + ": " if name else ''}{construction.output_type!s} <- {construction.source}"
    for parameter_name, parameter in construction.parameters:
        result += "\n" + _format_construction_string(
            parameter_name, parameter, indent, level + 1
        )
    return result


def format_construction_string(
    construction: Construction, indent: int = 2
) -> str:
    return _format_construction_string("", construction, indent, 0)


class ConstructorCache(Protocol[T]):
    def __setitem__(self, key: Construction, value: T) -> None:
        raise NotImplementedError()

    def __getitem__(self, item: Construction) -> T:
        raise NotImplementedError()

    def get(self, key: Construction, default: T, /) -> T:
        raise NotImplementedError()


class ConstructorSaveTo(Protocol):
    def __setitem__(self, key: type[Any], value: Any) -> None:
        raise NotImplementedError()


_undefined = object()


class Constructor:

    _cache: ConstructorCache[Any] | None

    def __init__(
        self,
        cache: ConstructorCache | None = _undefined,  # type: ignore[assignment]
        save_to: ConstructorSaveTo | None = None,
    ) -> None:
        self._cache = {} if cache is _undefined else cache
        self._save_to = save_to

    async def construct(self, construction: Construction[T]) -> T:
        if self._cache:
            value = self._cache.get(construction, None)
            if value is not None:
                return await value
        coroutine = self._construct(construction)
        if self._cache:
            # We cache the coroutine instead of the result
            # This allows asynchronous requests to share the same coroutine
            self._cache[construction] = coroutine
        value = await coroutine
        if self._save_to:
            self._save_to[construction.output_type] = value
        return value

    async def _construct(self, construction: Construction[T]) -> T:
        parameter_name_coroutines = tuple(
            (name, self.construct(param))
            for name, param in construction.parameters
        )

        names = tuple(p[0] for p in parameter_name_coroutines)
        coroutines = tuple(p[1] for p in parameter_name_coroutines)

        results = tuple(await asyncio.gather(*coroutines))

        parameters = {name: result for name, result in zip(names, results)}

        if construction.is_async:
            return await construction.constructor(**parameters)  # type: ignore[misc]
        else:
            return construction.constructor(**parameters)  # type: ignore[return-value]
