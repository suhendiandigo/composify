from abc import ABC, abstractmethod
from bisect import insort
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Generic, TypeVar, get_origin

from composify.errors import (
    AmbiguousInstanceError,
    ConflictingInstanceNameError,
    InstanceOfNameNotFoundError,
    InstanceOfTypeNotFoundError,
    InvalidTypeAnnotation,
    MultiplePrimaryInstanceError,
)
from composify.get import Get
from composify.metadata import Name, collect_attributes
from composify.metadata.attributes import AttributeSet
from composify.registry import (
    EntriesCollator,
    EntriesFilterer,
    Entry,
    Key,
    TypedRegistry,
)
from composify.types import AnnotatedType, get_type, resolve_type_name

E = TypeVar("E")

ARRAY_TYPES = {
    list: list,
    tuple: tuple,
    Iterable: tuple,
    Collection: tuple,
    set: set,
}


@dataclass(frozen=True)
class InstanceWrapper(Entry, Generic[E]):
    instance: E = field(hash=False, compare=False)
    instance_type: type[E]
    instance_name: str
    attributes: AttributeSet
    is_primary: bool
    priority: int

    @property
    def key(self) -> Key:
        return self.instance_type

    @property
    def name(self) -> str:
        return self.instance_name

    def __call__(self) -> E:
        return self.instance

    def __repr__(self) -> str:
        return f"Instance(name={self.name}, type={self.instance_type!r}, value={self.instance!r}, attributes={self.attributes!r}, is_primary={self.is_primary!r})"


def _resolve_instance_name(value: Any):
    return resolve_type_name(value.__class__)


class ContainerDefaultEntriesCollator(EntriesCollator[InstanceWrapper]):
    def collate_entries(
        self, entry: InstanceWrapper, entries: list[InstanceWrapper]
    ) -> None:
        for other in entries:
            if entry.instance_name == other.instance_name:
                raise ConflictingInstanceNameError(
                    entry.instance_name, entry, other
                )
            if entry.is_primary and other.is_primary:
                raise MultiplePrimaryInstanceError(entry, other)
        insort(entries, entry, key=InstanceWrapper.ordering)


def _ensure_type(
    type_: AnnotatedType | None,
) -> AnnotatedType:
    if type_ is None:
        raise InvalidTypeAnnotation("Missing a type.")
    if not isinstance(type_, type):
        origin = get_origin(type_)
        if origin is not Annotated:
            raise InvalidTypeAnnotation(
                f"Input must be a type, got {type_} of type {type(type_)}."
            )
    return type_


class BaseContainer(ABC):
    @abstractmethod
    def add(
        self,
        instance: Any,
        type_: AnnotatedType | None = None,
        *,
        name: str | None = None,
        is_primary: bool = False,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    def remove(self, instance: Any) -> None:
        raise NotImplementedError()

    @abstractmethod
    def remove_by_name(self, name: str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def __setitem__(self, key: str | type, value: Any):
        raise NotImplementedError()

    @abstractmethod
    def __getitem__(self, item: type[E]) -> E | None:
        raise NotImplementedError()

    @abstractmethod
    def __delitem__(self, key):
        raise NotImplementedError()

    @abstractmethod
    def get(self, type_: type[E]) -> E | None:
        raise NotImplementedError()

    @abstractmethod
    def get_wrapper(self, type_: type[E]) -> InstanceWrapper[E]:
        raise NotImplementedError()

    @abstractmethod
    def get_by_name(self, name: str, _: type[E] | None = None) -> E:
        raise NotImplementedError()


class Container(BaseContainer):
    __slots__ = (
        "_name",
        "_mapping_by_type",
        "_mapping_by_name",
    )

    _mapping_by_type: TypedRegistry[InstanceWrapper]
    _mapping_by_name: dict[str, InstanceWrapper]

    def __init__(
        self,
        name: str | None = None,
        *,
        attribute_filterer: EntriesFilterer | None = None,
        entries_collator: EntriesCollator | None = None,
    ):
        self._name = name or hex(self.__hash__())
        self._mapping_by_type = TypedRegistry(
            entries_filterer=attribute_filterer,
            entries_collator=entries_collator
            or ContainerDefaultEntriesCollator(),
        )
        self._mapping_by_name = {}

    def __str__(self) -> str:
        return f"container::{self._name}"

    def _resolve_name(self, instance: str) -> str:
        name = _resolve_instance_name(instance)
        i = 0
        resolved_name = f"{name}_{i}"
        while resolved_name in self._mapping_by_name:
            i += 1
            resolved_name = f"{name}_{i}"
        return resolved_name

    def add(
        self,
        instance: Any,
        type_: AnnotatedType | None = None,
        *,
        name: str | None = None,
        is_primary: bool = False,
        priority: int = 0,
    ) -> None:
        type_ = _ensure_type(type_ or instance.__class__)

        attributes = collect_attributes(type_)
        instance_type = get_type(type_)

        name = name or attributes.get(Name)

        if name is None:
            name = self._resolve_name(instance)
        elif name in self._mapping_by_name:
            raise ConflictingInstanceNameError(
                name, instance, self._mapping_by_name[name]
            )

        wrapper = InstanceWrapper(
            instance,
            instance_type=instance_type,
            instance_name=name,
            attributes=AttributeSet((*attributes, name)),
            is_primary=is_primary,
            priority=priority,
        )

        self._mapping_by_name[name] = wrapper
        self._mapping_by_type.add_entry(wrapper)

    def remove(self, instance: Any) -> None:
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

    def __setitem__(self, key: str | type, value: Any):
        if isinstance(key, str):
            self.add(value, name=key)
        else:
            self.add(value, type_=key)

    def __getitem__(self, item: type[E]) -> E | None:
        return self.get(item)

    def __delitem__(self, key):
        self.remove(key)

    def get(self, type_: AnnotatedType[E]) -> E:
        return self.get_wrapper(type_).instance

    def get_wrapper(self, type_: AnnotatedType[E]) -> InstanceWrapper[E]:
        type_ = _ensure_type(type_=type_)
        wrappers = self._mapping_by_type.get(type_)
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
        if primary is not None:
            return primary
        raise AmbiguousInstanceError(type_, wrappers)

    def get_all(self, type_: AnnotatedType[E]) -> Sequence[E]:
        return tuple(  # type: ignore[var-annotated]
            wrapper.instance for wrapper in self.get_all_wrapper(type_)
        )

    def get_all_wrapper(
        self, type_: AnnotatedType[E]
    ) -> Sequence[InstanceWrapper[E]]:
        type_ = _ensure_type(type_=type_)
        return tuple(self._mapping_by_type.get(type_))

    def get_by_name(self, name: str, _: type[E] | None = None) -> E:
        try:
            return self._mapping_by_name[name].instance
        except KeyError:
            raise InstanceOfNameNotFoundError(name)


class ContainerGetter(Get):
    def __init__(self, container: Container) -> None:
        super().__init__()
        self._container = container

    def one(
        self,
        type_: AnnotatedType[E],
    ) -> E:
        return self._container.get(type_)

    def all(self, type_: AnnotatedType[E]) -> Sequence[E]:
        return self._container.get_all(type_)
