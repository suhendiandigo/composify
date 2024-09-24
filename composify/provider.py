from dataclasses import dataclass
from typing import Annotated, Any, Generic, Iterable, Protocol, TypeVar

from composify.constructor import Constructor
from composify.container import Container
from composify.errors import InstanceNotFoundError
from composify.metadata.attributes import ProvidedBy
from composify.rules import RuleRegistry

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
            if wrapper.attributes.get(ProvidedBy, None) is not None:
                # This is to prevent container from providing instances
                # provided by other providers.
                return
            source = f"{self._container}::{wrapper.name}"
            yield Constructor(
                source=source,
                constructor=wrapper,
                is_async=False,
                output_type=Annotated[type_, ProvidedBy(source)],
                dependencies=tuple(),
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
            source = f"rule::{rule.canonical_name}"
            yield Constructor(
                source=source,
                constructor=rule.function,
                is_async=rule.is_async,
                output_type=Annotated[type_, ProvidedBy(source)],
                dependencies=rule.parameter_types,
            )
