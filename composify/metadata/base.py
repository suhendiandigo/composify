"""Base implementation for all annotated metadata."""

from functools import partial
from typing import Any, TypeVar, cast

from typing_extensions import Self

from composify.types import AnnotatedType


class BaseMetadata:
    """Base class for all annotated metadata."""

    __slots__ = ()


M = TypeVar("M", bound=BaseMetadata)
T = TypeVar("T")


class MetadataSet(frozenset[M]):
    """A frozenset of BaseMetadata."""

    _mapping: dict[type[M], M] | None

    def __new__(cls, *args, **kwargs) -> Self:
        """Create new MetadataSet."""
        self = super().__new__(cls, *args, **kwargs)
        self._mapping = None

        return self

    def _generate_mapping(self) -> dict[type[M], M]:
        return {type(metadata): metadata for metadata in self}

    def get(self, key: type[T], default: T | None = None) -> T | None:
        """Get a metadata value.

        Args:
            key (type[T]): The Metadata type to retrieve.
            default (T | None, optional): Returned if the key does not exist in the set. Defaults to None.

        Returns:
            T | None: The metadata object.
        """
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
    vals: tuple[Any, ...] = getattr(type_, "__metadata__", ())
    if not vals:
        return set_type(vals)
    return set_type(filter(partial(_is_instance, metadata_type), vals))


def collect_metadata(type_: AnnotatedType) -> MetadataSet:
    """Collect all annotated metadata that inherits BaseMetadata class as a frozenset."""
    return _collect_metadata(type_, BaseMetadata, MetadataSet)
