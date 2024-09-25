from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar

from composify.attributes import ProvidedBy
from composify.constructor import Constructor
from composify.container import Container
from composify.errors import InstanceNotFoundError
from composify.rules import ConstructRule, RuleRegistry
from composify.types import AnnotatedType

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
    def provide_for_type(
        self, type_: AnnotatedType[T]
    ) -> Iterable[Constructor[T]]:
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

    def provide_for_type(
        self, type_: AnnotatedType[T]
    ) -> Iterable[Constructor[T]]:
        try:
            wrapper = self._container.get_wrapper(type_)  # type: ignore[var-annotated]
            if wrapper.attributes.get(ProvidedBy, None) is not None:
                # This is to prevent container from providing instances
                # provided by other providers.
                return
            yield Constructor(
                source=f"{self._container}::{wrapper.name}",
                constructor=wrapper,
                is_async=False,
                output_type=type_,
                dependencies=(),
            )
        except InstanceNotFoundError:
            pass


class RuleBasedConstructorProvider(ConstructorProvider):
    __slots__ = ("_rules",)

    _rules: RuleRegistry

    def __init__(self, rules: RuleRegistry) -> None:
        self._rules = rules

    def provide_for_type(
        self, type_: AnnotatedType[T]
    ) -> Iterable[Constructor[T]]:
        rules: Iterable[ConstructRule[T]] = self._rules.get(type_)
        if not rules:
            return
        for rule in rules:
            yield Constructor(
                source=f"rule::{rule.canonical_name}",
                constructor=rule.function,
                is_async=rule.is_async,
                output_type=type_,
                dependencies=rule.parameter_types,
            )
