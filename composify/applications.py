import asyncio
from typing import Callable, Iterable, Literal, TypeVar

from typing_extensions import TypeAlias

from composify.blueprint import Blueprint, BlueprintResolver
from composify.builder import AsyncBuilder, Builder
from composify.container import Container
from composify.errors import MultipleResolutionError, NoResolutionError
from composify.provider import (
    ConstructorProvider,
    ContainerInstanceProvider,
    RuleBasedConstructorProvider,
)
from composify.rules import ConstructRule, RuleRegistry, as_rule

T = TypeVar("T")


ResolutionMode: TypeAlias = Literal["default", "select_first"]


def _ensure_rule_type(rule: ConstructRule | Callable) -> ConstructRule:
    r = as_rule(rule)
    if r is None:
        raise TypeError(
            f"{rule!r} of type{type(rule)!r} is not a rule. To declare a rule, use the @rule decorator."
        )
    return r


class Composify:
    def __init__(
        self,
        name: str | None = None,
    ) -> None:
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

        self._container.add(self)
        self._container.add(self._container)

    def _select_blueprint(self, resolution_mode: ResolutionMode = "default"):
        match resolution_mode:
            case "select_first":
                return self._select_first_blueprint
            case _:
                return self._default_select_blueprint

    @property
    def container(self) -> Container:
        return self._container

    def add_rule(self, rule: ConstructRule | Callable) -> None:
        self._rules.register_rule(_ensure_rule_type(rule))
        self._resolver.clear_memo()

    def add_rules(self, rules: Iterable[ConstructRule]) -> None:
        self._rules.register_rules(
            r for rule in rules if (r := _ensure_rule_type(rule))
        )
        self._resolver.clear_memo()

    def register_provider(self, provider: ConstructorProvider) -> None:
        self._resolver.register_provider(provider)

    def _default_select_blueprint(
        self, type_: type[T], plans: tuple[Blueprint[T], ...]
    ) -> Blueprint[T]:
        if len(plans) > 1:
            raise MultipleResolutionError(type_, plans)
        elif len(plans) == 0:
            raise NoResolutionError(type_)
        return plans[0]

    def _select_first_blueprint(
        self, type_: type[T], plans: tuple[Blueprint[T], ...]
    ) -> Blueprint[T]:
        if len(plans) == 0:
            raise NoResolutionError(type_)
        return plans[0]

    async def aget(
        self, type_: type[T], resolution_mode: ResolutionMode = "default"
    ) -> T:
        plans = tuple(self._resolver.resolve(type_))
        plan = self._select_blueprint(resolution_mode)(type_, plans)
        return await self._async_builder.from_blueprint(plan)

    async def aget_all(self, type_: type[T]) -> Iterable[T]:
        plans = tuple(self._resolver.resolve(type_))
        return tuple(
            await asyncio.gather(
                *(self._async_builder.from_blueprint(plan) for plan in plans)
            )
        )

    def get(
        self, type_: type[T], resolution_mode: ResolutionMode = "default"
    ) -> T:
        plans = tuple(self._resolver.resolve(type_))
        plan = self._select_blueprint(resolution_mode)(type_, plans)
        return self._builder.from_blueprint(plan)

    def get_all(self, type_: type[T]) -> Iterable[T]:
        plans = tuple(self._resolver.resolve(type_))
        return tuple(self._builder.from_blueprint(plan) for plan in plans)
