import sys
from functools import partial
from typing import Any, Self, TypeVar, cast

if sys.version_info < (3, 10):
    SLOTS = {}
else:
    SLOTS = {"slots": True}


class BaseMetadata:
    __slots__ = ()


M = TypeVar("M", bound=BaseMetadata)
T = TypeVar("T")


class MetadataSet(frozenset[M]):

    _mapping: dict[type[M], M] | None

    def __new__(cls, *args, **kwargs) -> Self:
        self = super().__new__(cls, *args, **kwargs)
        self._mapping = None

        return self

    def _generate_mapping(self) -> dict[type[M], M]:
        return {type(metadata): metadata for metadata in self}

    def get(self, key: type[T], default: T | None = None) -> T | None:
        if self._mapping is None:
            self._mapping = self._generate_mapping()
        return cast(T, self._mapping.get(cast(type[M], key), default))

    def __getitem__(self, key: type[T]) -> T:
        if self._mapping is None:
            self._mapping = self._generate_mapping()
        return cast(T, self._mapping[cast(type[M], key)])


def _is_instance(type_: type, instance: Any) -> bool:
    return isinstance(instance, type_)


S = TypeVar("S", bound=MetadataSet)


def _collect_metadata(
    type_: type,
    metadata_type: type,
    set_type: type[S],
) -> S:
    vals: tuple[Any, ...] = getattr(type_, "__metadata__", tuple())
    if not vals:
        return set_type(vals)
    return set_type(filter(partial(_is_instance, metadata_type), vals))


def collect_metadata(type_: type) -> MetadataSet:
    """Collect all annotated metadata that inherits BaseMetadata class as a frozenset."""
    return _collect_metadata(type_, BaseMetadata, MetadataSet)
