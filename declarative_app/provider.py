from dataclasses import dataclass
from typing import Any, Generic, Iterable, Protocol, TypeVar

from declarative_app.constructor import Constructor
from declarative_app.container import Container, InstanceNotFoundError
from declarative_app.rules import RuleRegistry

__all__ = [
    "ConstructorProvider",
    "ContainerInstanceProvider",
    "RuleBasedConstructorProvider",
]


T = TypeVar("T")


@dataclass(frozen=True)
class Static(Generic[T]):
    value: T

    def __call__(self) -> Any:
        return self.value


class ConstructorProvider(Protocol):

    def provide_for_type(self, type_: type[T]) -> Iterable[Constructor[T]]:
        raise NotImplementedError()


class ContainerInstanceProvider(ConstructorProvider):
    __slots__ = ("_container",)

    def __init__(
        self,
        container: Container,
    ) -> None:
        self._container = container

    @property
    def container(self) -> Container:
        return self._container

    def provide_for_type(self, type_: type[T]) -> Iterable[Constructor[T]]:
        try:
            wrapper = self._container.get_wrapper(type_)
            yield Constructor(
                source=f"{self._container}::{wrapper.name}",
                constructor=Static(wrapper.instance),
                is_async=False,
                output_type=type_,
                dependencies=frozenset(),
            )
        except InstanceNotFoundError:
            pass


class RuleBasedConstructorProvider(ConstructorProvider):
    __slots__ = ("_rules",)

    _rules: RuleRegistry

    def __init__(self, rules: RuleRegistry) -> None:
        self._rules = rules

    def provide_for_type(self, type_: type[T]) -> Iterable[Constructor[T]]:
        rules = self._rules.get(type_)
        if not rules:
            return
        for rule in rules:
            yield Constructor(
                source=f"rule::{rule.cannonical_name}",
                constructor=rule.function,
                is_async=rule.is_async,
                output_type=type_,
                dependencies=rule.parameter_types,
            )
