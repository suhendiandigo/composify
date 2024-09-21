import asyncio
from dataclasses import dataclass, field
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


_ConstructorFunction: TypeAlias = (
    Callable[..., Awaitable[T]] | Callable[..., T]
)


@dataclass(frozen=True)
class ConstructionPlan(Generic[T]):
    name: str
    constructor: _ConstructorFunction[T]
    is_async: bool
    output_type: type[T]
    dependencies: Mapping[str, type]


@dataclass(frozen=True)
class Construction(Generic[T]):
    name: str = field(hash=False)
    constructor: _ConstructorFunction[T]
    is_async: bool = field(hash=False)
    output_type: type[T] = field(hash=False)
    parameters: Mapping[str, "Construction"]
    chain_length: int = field(hash=False)


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
                name=f"{self._container}",
                constructor=Static(val),
                is_async=False,
                output_type=type_,
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
                    output_type=type_,
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

    def _resolve(
        self, target: type[T], name: str, trace: Tracing
    ) -> Iterable[Construction[T]]:
        plans = self._create_plans(target)
        if not plans:
            raise FailedToResolveError(target, trace.traces)
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
                        output_type=plan.output_type,
                        parameters=parameter_permutation,
                        chain_length=level,
                    )
            else:
                yield Construction(
                    name=plan.name,
                    constructor=plan.constructor,
                    is_async=plan.is_async,
                    output_type=plan.output_type,
                    parameters={},
                    chain_length=0,
                )

    def resolve(self, target: type[T]) -> Iterable[Construction[T]]:
        tracing = Tracing(tuple())
        return sorted(
            self._resolve(target, "__root__", tracing),
            key=lambda x: x.chain_length,
        )


def _format_construction_string(
    name: str, construction: Construction, indent: int, level: int
) -> str:
    indent_str = " " * (level * indent)
    result = f"{indent_str}{name + ": " if name else ''}{construction.output_type!s} <- {construction.name}"
    for parameter_name, parameter in construction.parameters.items():
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
            for name, param in construction.parameters.items()
        )

        names = tuple(p[0] for p in parameter_name_coroutines)
        coroutines = tuple(p[1] for p in parameter_name_coroutines)

        results = tuple(await asyncio.gather(*coroutines))

        parameters = {name: result for name, result in zip(names, results)}

        if construction.is_async:
            return await construction.constructor(**parameters)  # type: ignore[misc]
        else:
            return construction.constructor(**parameters)  # type: ignore[return-value]
