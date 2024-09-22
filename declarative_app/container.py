from collections import abc
from dataclasses import dataclass
from typing import Any, Generic, Iterable, Type, TypeVar

from declarative_app.metadata import Name, get_attributes
from declarative_app.metadata.attributes import AttributeSet, resolve_name
from declarative_app.metadata.qualifiers import VarianceType
from declarative_app.registry import (
    AttributeFilterer,
    Entry,
    Key,
    TypedRegistry,
    UniqueEntryValidator,
)
from declarative_app.types import get_type

from .errors import (
    AmbiguousInstanceError,
    ConflictingInstanceNameError,
    InstanceOfNameNotFoundError,
    InstanceOfTypeNotFoundError,
    MultiplePrimaryInstanceError,
)

E = TypeVar("E")

ARRAY_TYPES = {
    list: list,
    tuple: tuple,
    abc.Iterable: tuple,
    abc.Collection: tuple,
    set: set,
}


@dataclass(frozen=True)
class InstanceWrapper(Entry, Generic[E]):
    instance: E
    instance_type: Type[E]
    instance_name: str
    attributes: AttributeSet
    is_primary: bool

    @property
    def key(self) -> Key:
        return self.instance_type

    @property
    def name(self) -> str:
        return self.instance_name

    def __repr__(self) -> str:
        return f"Instance(name={self.name}, value={self.instance!r})"


def _resolve_instance_name(value: Any):
    return (
        f"{value.__class__.__module__}.{value.__class__.__qualname__}".replace(
            ".<locals>", ""
        )
    )


class ContainerAttributeFilterer(AttributeFilterer[InstanceWrapper]):

    def match_entry_attributes(
        self, entry: InstanceWrapper, attributes: AttributeSet
    ) -> bool:
        return entry.attributes.issuperset(attributes)


class ContainerUniqueEntryValidator(UniqueEntryValidator[InstanceWrapper]):

    def validate_uniqueness(
        self, entry: InstanceWrapper, others: Iterable[InstanceWrapper]
    ) -> None:
        for other in others:
            if entry.instance_name == other.instance_name:
                raise ConflictingInstanceNameError(
                    entry.instance_name, entry, other
                )
            if entry.is_primary and other.is_primary:
                raise MultiplePrimaryInstanceError(entry, other)


class Container:
    __slots__ = (
        "_name",
        "_mapping_by_type",
        "_mapping_by_name",
        "_default_variance",
    )

    _mapping_by_type: TypedRegistry[InstanceWrapper]
    _mapping_by_name: dict[str, InstanceWrapper]

    def __init__(
        self,
        name: str | None = None,
        default_variance: VarianceType = "covariant",
    ):
        self._name = name or hex(self.__hash__())
        self._mapping_by_type = TypedRegistry(
            default_variance=default_variance,
            attribute_filterer=ContainerAttributeFilterer(),
            unique_validator=ContainerUniqueEntryValidator(),
        )
        self._mapping_by_name = {}
        self._default_variance = default_variance

    def __str__(self) -> str:
        return f"container::{self._name}"

    def add(
        self,
        instance: Any,
        *,
        name: str | None = None,
        is_primary: bool = False,
    ) -> None:
        """Add an object to the object registry under a specific name.
        :param name: The identifier of the object in the registry.
        :param component: The object to be added to the registry.
        :return:
        """
        type_ = instance.__class__

        attributes = get_attributes(type_)
        instance_type = get_type(type_)

        name = name or resolve_name(attributes)

        if name is None:
            i = 0
            resolved_name = _resolve_instance_name(instance)
            name = f"{resolved_name}_{i}"
            while name in self._mapping_by_name:
                i += 1
                name = f"{resolved_name}_{i}"
        elif name in self._mapping_by_name:
            raise ConflictingInstanceNameError(
                name, instance, self._mapping_by_name[name]
            )

        wrapper = InstanceWrapper(
            instance,
            instance_type=instance_type,
            instance_name=name,
            attributes=frozenset(tuple(attributes) + (Name(name),)),
            is_primary=is_primary,
        )

        self._mapping_by_name[name] = wrapper
        self._mapping_by_type.add_entry(wrapper)

    def remove(self, instance: Any) -> None:
        """Remove an object from the object registry."""
        type_ = get_type(instance.__class__)
        wrappers = self._mapping_by_type.get(type_)
        if wrappers:
            wrapper = None
            for wrapper in wrappers:
                if wrapper.instance == instance:
                    break
            if wrapper is not None:
                self._mapping_by_type.remove_entry(wrapper)
                del self._mapping_by_name[wrapper.instance_name]

    def remove_by_name(self, name: str) -> None:
        try:
            wrapper = self._mapping_by_name[name]
        except KeyError:
            raise InstanceOfNameNotFoundError(name)
        del self._mapping_by_name[name]

        self._mapping_by_type.remove_entry(wrapper)

    def __setitem__(self, key: str, value: Any):
        self.add(value, name=key)

    def __getitem__(self, item: Type[E]) -> E | None:
        return self.get(item)

    def __delitem__(self, key):
        self.remove(key)

    def get(self, type_: Type[E]) -> E | None:
        """Get an object from the object registry."""
        wrapper = self.get_wrapper(type_)
        return wrapper.instance if wrapper else None

    def get_wrapper(self, type_: Type[E]) -> InstanceWrapper[E]:
        """Get an object from the object registry."""
        wrappers = tuple(self._mapping_by_type.get(type_))
        if not wrappers:
            raise InstanceOfTypeNotFoundError(type_)
        if len(wrappers) == 1:
            return wrappers[0]
        primary = None
        for wrapper in wrappers:
            if wrapper.is_primary:
                if primary is None:
                    primary = wrapper
                else:
                    raise MultiplePrimaryInstanceError()
        if primary:
            return primary
        raise AmbiguousInstanceError(type_, wrappers)

    def get_by_name(self, name: str, _: Type[E] | None = None) -> E:
        try:
            return self._mapping_by_name[name].instance
        except KeyError:
            raise InstanceOfNameNotFoundError(name)
