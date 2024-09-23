from abc import ABC, abstractmethod
from asyncio import Protocol
from bisect import insort
from dataclasses import dataclass
from typing import Generic, Iterable, TypeAlias, TypeVar

from declarative_app.metadata.attributes import (
    AttributeSet,
    collect_attributes,
)
from declarative_app.metadata.qualifiers import (
    DisallowSubclass,
    QualifierSet,
    VarianceType,
    collect_qualifiers,
)
from declarative_app.types import get_type, resolve_base_types

Key: TypeAlias = type


class Entry(ABC):
    @property
    @abstractmethod
    def key(self) -> Key:
        raise NotImplementedError()

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError()

    attributes: AttributeSet


E = TypeVar("E", bound=Entry)


class RegistryError(Exception):
    pass


class DuplicatedEntryError(RegistryError, Generic[E]):

    def __init__(self, to_add: E, existing: E) -> None:
        self.to_add = to_add
        self.existing = existing
        super().__init__(
            f"Entry {to_add!r} conflict with existing entry {existing!r}"
        )


def _entry_ordering(entry: Entry) -> int:
    return len(entry.key.mro())


@dataclass(frozen=True)
class FilteringContext:
    key: Key
    attributes: AttributeSet
    qualifiers: QualifierSet


class EntriesFilterer(Protocol, Generic[E]):

    def fitler_entries(
        self, entries: Iterable[E], context: FilteringContext
    ) -> Iterable[E]:
        raise NotImplementedError()


_DEFAULT_DISALLOW_SUBCLASS = DisallowSubclass(False)


class DefaultEntriesFilterer(EntriesFilterer[E]):

    def fitler_entries(
        self, entries: Iterable[E], context: FilteringContext
    ) -> Iterable[E]:
        if context.attributes and (
            filtered := tuple(
                entry
                for entry in entries
                if entry.attributes.issuperset(context.attributes)
            )
        ):
            entries = filtered
        if entries:
            if context.qualifiers.get(DisallowSubclass):
                entries = tuple(
                    filter(lambda x: type(x) is context.key, entries)
                )
        return entries


class EntriesValidator(Protocol, Generic[E]):
    """Raise errors if a new entry do not fit with existing entries.
    Because of duplicated value, etc."""

    def validate_entries(self, entry: E, others: Iterable[E]) -> None:
        raise NotImplementedError()


class DefaultEntriesValidator(EntriesValidator[E]):
    """By default we only validate based on equality."""

    def validate_entries(self, entry: E, others: Iterable[E]) -> None:
        for other in others:
            if entry == other:
                raise DuplicatedEntryError(entry, other)


_EMPTY_RESULT: tuple = tuple()


class TypedRegistry(Generic[E]):

    __slots__ = (
        "_entries",
        "_default_variance",
        "_entries_filterer",
        "_unique_validator",
    )

    _entries: dict[Key, list[E]]

    def __init__(
        self,
        initial_entries: Iterable[E] | None = None,
        *,
        default_variance: VarianceType = "covariant",
        entries_filterer: EntriesFilterer[E] | None = None,
        unique_validator: EntriesValidator[E] | None = None,
    ) -> None:
        self._entries = {}
        self._default_variance = default_variance
        self._entries_filterer = entries_filterer or DefaultEntriesFilterer()
        self._unique_validator = unique_validator or DefaultEntriesValidator()
        if initial_entries is not None:
            self.add_entries(initial_entries)

    def _validate_uniqueness(self, entry: E, others: Iterable[E]) -> None:
        self._unique_validator.validate_entries(entry, others)

    def _add_entry(self, key: Key, entry: E) -> None:
        if key in self._entries:
            entries = self._entries[key]
            self._validate_uniqueness(entry, entries)
            # We want to keep the entries ordered
            # by how derived the key type is
            # we are prioritizing the less derived type
            insort(entries, entry, key=_entry_ordering)
        else:
            self._entries[key] = [entry]

    def add_entry(self, entry: E) -> None:
        for type_ in resolve_base_types(entry.key):
            self._add_entry(type_, entry)

    def add_entries(self, entries: Iterable[E]) -> None:
        for entry in entries:
            self.add_entry(entry)

    def _remove_entry(self, key: Key, entry: E) -> None:
        if key in self._entries:
            entries = self._entries[key]
            entries.remove(entry)
            if not entries:
                del self._entries[key]

    def remove_entry(self, entry: E) -> None:
        for type_ in resolve_base_types(entry.key):
            self._remove_entry(type_, entry)

    def _filter_entries(self, key: Key, entries: Iterable[E]) -> Iterable[E]:
        if self._entries_filterer is None:
            return entries
        return self._entries_filterer.fitler_entries(
            entries,
            FilteringContext(
                key=key,
                attributes=collect_attributes(key),
                qualifiers=collect_qualifiers(key),
            ),
        )

    def _get_entries(self, key: Key) -> Iterable[E]:
        type_ = get_type(key)

        entries: Iterable[E] = self._entries.get(type_, _EMPTY_RESULT)
        if entries:
            entries = self._filter_entries(key, entries)

        return entries

    def get(self, key: Key) -> tuple[E, ...]:
        entries: Iterable[E] = self._get_entries(key)
        if not entries:
            return _EMPTY_RESULT

        return tuple(entries)
