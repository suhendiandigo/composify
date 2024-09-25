from abc import ABC, abstractmethod
from asyncio import Protocol
from bisect import insort
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar

from composify._qualifiers import DisallowSubclass
from composify.errors import DuplicatedEntryError
from composify.metadata.attributes import AttributeSet, collect_attributes
from composify.metadata.qualifiers import QualifierSet, collect_qualifiers
from composify.types import AnnotatedType, get_type, resolve_base_types

Key: TypeAlias = AnnotatedType


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
    priority: int

    @staticmethod
    def ordering(entry: "Entry") -> tuple[int, ...]:
        # We want to keep the entries ordered
        # by how derived the key type is
        # we are prioritizing the less derived type

        # We want higher priority to be ordered first
        return (-entry.priority, len(entry.key.mro()))


E = TypeVar("E", bound=Entry)


@dataclass(frozen=True)
class FilteringContext:
    key: Key
    attributes: AttributeSet
    qualifiers: QualifierSet


class EntriesFilterer(Protocol, Generic[E]):
    def filter_entries(
        self, entries: Iterable[E], context: FilteringContext
    ) -> Iterable[E]:
        raise NotImplementedError()


class DefaultEntriesFilterer(EntriesFilterer[E]):
    def filter_entries(
        self, entries: Iterable[E], context: FilteringContext
    ) -> Iterable[E]:
        if context.attributes:
            entries = tuple(
                entry
                for entry in entries
                if entry.attributes.issuperset(context.attributes)
            )
        if entries:
            if context.qualifiers.get(DisallowSubclass):
                entries = tuple(
                    filter(lambda x: type(x) is context.key, entries)
                )
        return entries


class EntriesCollator(Protocol, Generic[E]):
    """Combine entries together.
    Raise errors if a new entry do not fit with existing entries.
    Because of duplicated value, etc.
    """

    def collate_entries(self, entry: E, entries: list[E]) -> None:
        """Collate entries.

        Args:
            entry (E): Entry to add.
            entries (list[E]): Entries to add to

        """
        raise NotImplementedError()


class DefaultEntriesCollator(EntriesCollator[E]):
    """By default we only validate based on equality."""

    def collate_entries(self, entry: E, entries: list[E]) -> None:
        """Collate entries.

        Args:
            entry (E): Entry to add.
            entries (list[E]): Entries to add to

        Raises:
            DuplicatedEntryError: If entries are duplicated.
        """
        for other in entries:
            if entry == other:
                raise DuplicatedEntryError(entry, other)
        insort(entries, entry, key=Entry.ordering)


_EMPTY_RESULT: tuple = ()


class TypedRegistry(Generic[E]):
    __slots__ = (
        "_entries",
        "_entries_filterer",
        "_entries_collator",
    )

    _entries: dict[Key, list[E]]

    def __init__(
        self,
        initial_entries: Iterable[E] | None = None,
        *,
        entries_filterer: EntriesFilterer[E] | None = None,
        entries_collator: EntriesCollator[E] | None = None,
    ) -> None:
        self._entries = {}
        self._entries_filterer = entries_filterer or DefaultEntriesFilterer()
        self._entries_collator = entries_collator or DefaultEntriesCollator()
        if initial_entries is not None:
            self.add_entries(initial_entries)

    def _collate_entries(self, entry: E, entries: list[E]) -> None:
        self._entries_collator.collate_entries(entry, entries)

    def _add_entry(self, key: Key, entry: E) -> None:
        type_ = get_type(key)
        if key in self._entries:
            entries = self._entries[type_]
            self._collate_entries(entry, entries)
        else:
            self._entries[type_] = [entry]

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
        return self._entries_filterer.filter_entries(
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

    def get(self, key: Key) -> Sequence[E]:
        entries: Iterable[E] = self._get_entries(key)
        if not entries:
            return _EMPTY_RESULT

        return tuple(entries)
