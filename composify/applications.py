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
    rule = as_rule(rule)
    if rule is None:
        raise TypeError(
            f"{rule!r} of type{type(rule)!r} is not a rule. To declare a rule, use the @rule decorator."
        )
    return rule


class Composify:
    def __init__(
        self,
        name: str | None = None,
        *,
        resolution_mode: ResolutionMode = "default",
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

        match resolution_mode:
            case "select_first":
                self._select_blueprint = self._select_first_blueprint
            case _:
                self._select_blueprint = self._default_select_blueprint

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

    async def async_build(self, type_: type[T]) -> T:
        plans = tuple(self._resolver.resolve(type_))
        plan = self._select_blueprint(type_, plans)
        return await self._async_builder.from_blueprint(plan)

    def build(self, type_: type[T]) -> T:
        plans = tuple(self._resolver.resolve(type_))
        plan = self._select_blueprint(type_, plans)
        return self._builder.from_blueprint(plan)
