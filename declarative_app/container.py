from collections import abc
from dataclasses import dataclass, field
from typing import (  # type: ignore[attr-defined]
    Any,
    Generic,
    Iterable,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from declarative_app.metadata import Name, get_attributes
from declarative_app.types import resolve_base_types

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
class InstanceWrapper(Generic[E]):
    instance: E
    resolved_types: tuple[type, ...]
    name: str
    is_primary: bool

    def __repr__(self) -> str:
        return f"Instance(name={self.name}, value={self.instance!r})"


@dataclass()
class WrapperGroup(Generic[E]):
    elements: list[InstanceWrapper[E]] = field(default_factory=list)
    primary: InstanceWrapper[E] | None = None

    def add(self, instance: InstanceWrapper[E]) -> None:
        self.elements.append(instance)
        if instance.is_primary:
            if self.primary is not None:
                raise MultiplePrimaryInstanceError(instance, self.primary)
            self.primary = instance

    def remove(self, instance: InstanceWrapper[E]) -> None:
        self.elements.remove(instance)

    def get_wrapper(self, instance: E) -> InstanceWrapper[E] | None:
        for e in self.elements:
            if e.instance is instance:
                return e
        return None

    @property
    def is_empty(self) -> bool:
        return len(self.elements) == 0

    def __iter__(self):
        return iter(self.elements)

    def __len__(self):
        return len(self.elements)

    def __getitem__(self, key) -> InstanceWrapper:
        return self.elements[key]


def _resolve_instance_name(value: Any):
    return (
        f"{value.__class__.__module__}.{value.__class__.__qualname__}".replace(
            ".<locals>", ""
        )
    )


class Container:
    __slots__ = ("_name", "_mapping_by_type", "_mapping_by_name")

    _mapping_by_type: dict[Type, WrapperGroup]
    _mapping_by_name: dict[str, InstanceWrapper]

    def __init__(self, name: str | None = None):
        self._name = name or hex(self.__hash__())
        self._mapping_by_type = {}
        self._mapping_by_name = {}

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
        resolved_types = resolve_base_types(instance.__class__)

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
            resolved_types=resolved_types,
            name=name,
            is_primary=is_primary,
        )

        self._mapping_by_name[name] = wrapper

        for type_ in resolved_types:
            if type_ in self._mapping_by_type:
                group = self._mapping_by_type[type_]
            else:
                group = self._mapping_by_type[type_] = WrapperGroup()
            group.add(wrapper)

    def remove(self, instance: Any) -> None:
        """Remove an object from the object registry."""
        resolved_types = resolve_base_types(instance.__class__)

        self._remove_from_types(instance, resolved_types)

    def _remove_from_types(self, instance: Any, types: Iterable[type]) -> None:
        names = []
        for type_ in types:
            if type_ in self._mapping_by_type:
                type_bucket = self._mapping_by_type[type_]
                wrapper = type_bucket.get_wrapper(instance)
                if wrapper is None:
                    continue
                names.append(wrapper.name)
                type_bucket.remove(wrapper)
                if type_bucket.is_empty:
                    del self._mapping_by_type[type_]
        for name in names:
            del self._mapping_by_name[name]

    def remove_by_name(self, name: str) -> None:
        try:
            wrapper = self._mapping_by_name[name]
        except KeyError:
            raise InstanceOfNameNotFoundError(name)
        del self._mapping_by_name[name]

        resolved_types = resolve_base_types(wrapper.instance.__class__)
        for type_ in resolved_types:
            if type_ in self._mapping_by_type:
                type_bucket = self._mapping_by_type[type_]
                type_bucket.remove(wrapper)
                if type_bucket.is_empty:
                    del self._mapping_by_type[type_]

    def __setitem__(self, key, value):
        self.add(key, value)

    def __getitem__(self, item):
        return self.get(item)

    def __delitem__(self, key):
        self.remove(key)

    def get(self, type_: Type[E], default: Any = ...) -> E:
        """Get an object from the object registry."""
        origin = get_origin(type_)
        if origin in ARRAY_TYPES:
            wrapper_type = ARRAY_TYPES[origin]
            args = get_args(type_)
            return wrapper_type(self._get_all_of_type(args[0], default))
        return self.get_wrapper(type_, default).instance

    def get_wrapper(
        self, type_: Type[E], default: Any = ...
    ) -> InstanceWrapper[E]:
        """Get an object from the object registry."""
        return self._get_by_type(type_, default)

    def _get_by_type(
        self, type_: Type[E], default: Any = ...
    ) -> InstanceWrapper[E]:
        """Get an object by their type from object registry.
        :param type_: The type of object to get. An array type such as `List[E]` or `Tuple[E]` are resolvable.
        :param default: The default value returned if the object of type is not found.
        :raise ComponentNotFoundError: If object of type is not found and the type is not an iterable type.
        :return: An object of type.
        """
        origin = get_origin(type_)
        if origin == Union:
            return self._get_union_by_type(type_, default)

        return self._get_single_by_type(type_, default)

    def _get_all_of_type(
        self, type_: Type[E], default: Any = ...
    ) -> Iterable[E]:
        """Get all objects of a specific type.
        :param type_: The type of object to get.
        :param default: The default value returned if the object of type is not found.
        :return: An iterable in the form of a tuple."""
        if get_origin(type_) == Union:
            args = get_args(type_)
            result: list[E] = []
            for inner_type in args:
                result.extend(self._get_all_of_type(inner_type))
            return tuple(result)
        if type_ in self._mapping_by_type:
            wrappers = self._mapping_by_type[type_]
            return tuple(wrappers)
        if default is not ...:
            return default
        return tuple()

    def _get_union_by_type(
        self, type_: Type[E], default: Any = ...
    ) -> InstanceWrapper[E]:
        args = get_args(type_)
        for inner_type in args:
            try:
                return self._get_single_by_type(inner_type)
            except InstanceOfTypeNotFoundError:
                pass
        if default is not ...:
            return default
        raise InstanceOfTypeNotFoundError(type_)

    def _get_single_by_type(
        self, type_: Type[E], default: Any = ...
    ) -> InstanceWrapper[E]:
        type_, metadata = get_attributes(type_)
        names = []
        for meta in metadata:
            if isinstance(meta, Name):
                names.append(meta.name)
        if names:
            for qualifier in names:
                if qualifier in self._mapping_by_name:
                    return self._mapping_by_name[qualifier]
            raise InstanceOfTypeNotFoundError(type_)

        if type_ in self._mapping_by_type:
            wrappers = self._mapping_by_type[type_]
            if len(wrappers) == 1:
                wrapper = wrappers[0]
                if names:
                    if wrapper.name in names:
                        return wrapper
                else:
                    return wrapper
            elif len(wrappers) > 1:
                if names:
                    filtered = list(
                        filter(lambda x: x.name in names, wrappers)
                    )
                    if len(filtered) == 1:
                        return filtered[0]
                    elif len(filtered) > 1:
                        raise AmbiguousInstanceError(type_, tuple(filtered))
                else:
                    if wrappers.primary is not None:
                        return wrappers.primary
                    raise AmbiguousInstanceError(type_, tuple(wrappers))
        if default is not ...:
            return default
        raise InstanceOfTypeNotFoundError(type_)

    def get_by_name(self, name: str, _: Type[E] | None = None) -> E:
        try:
            return self._mapping_by_name[name].instance
        except KeyError:
            raise InstanceOfNameNotFoundError(name)
