from abc import ABC, abstractmethod
from asyncio import Protocol
from bisect import insort
from typing import Generic, Iterable, TypeAlias, TypeVar

from declarative_app.metadata.attributes import (
    AttributeCollection,
    get_attributes,
)
from declarative_app.metadata.qualifiers import (
    VarianceType,
    get_qualifiers,
    resolve_variance,
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


class AttributeFilterer(Protocol, Generic[E]):

    def match_entry_attributes(
        self, entry: E, attributes: AttributeCollection
    ) -> bool:
        raise NotImplementedError()


class EntryEqualityComparator(Protocol, Generic[E]):

    def are_equal(self, entry: E, other: E) -> bool:
        raise NotImplementedError()


class DefaultEntryEqualityComparator(EntryEqualityComparator[E]):

    def are_equal(self, entry: E, other: E) -> bool:
        return entry == other


class TypedRegistry(Generic[E]):

    __slots__ = (
        "_entries",
        "_default_variance",
        "_attribute_filterer",
        "_equality_comparator",
    )

    _entries: dict[Key, list[E]]

    def __init__(
        self,
        initial_entries: Iterable[E] | None = None,
        *,
        default_variance: VarianceType = "covariant",
        attribute_filterer: AttributeFilterer | None = None,
        equality_comparator: EntryEqualityComparator | None = None,
    ) -> None:
        self._entries = {}
        self._default_variance = default_variance
        self._attribute_filterer = attribute_filterer
        self._equality_comparator = (
            equality_comparator or DefaultEntryEqualityComparator()
        )
        if initial_entries is not None:
            self.add_entries(initial_entries)

    def _compare_entries(self, entry: E, other: E) -> bool:
        return self._equality_comparator.are_equal(entry, other)

    def _add_entry(self, key: Key, entry: E) -> None:
        if key in self._entries:
            rules = self._entries[key]
            for _rule in rules:
                if self._compare_entries(entry, _rule):
                    raise DuplicatedEntryError(entry, _rule)
            # We want to keep the entries ordered
            # by how derived the key type is
            # we are prioritizing the less derived type
            insort(rules, entry, key=_entry_ordering)
        else:
            self._entries[key] = [entry]

    def add_entry(self, entry: E) -> None:
        for type_ in resolve_base_types(entry.key):
            self._add_entry(type_, entry)

    def add_entries(self, entries: Iterable[E]) -> None:
        for rule in entries:
            self.add_entry(rule)

    def _get_entries(self, key: Key, variance: VarianceType) -> list[E]:
        if variance == "invariant":
            return list(
                filter(
                    lambda x: x.key is key,
                    self._entries.get(key, []),
                )
            )
        elif variance == "contravariant":
            entries = set()
            for parent_type in resolve_base_types(key):
                for entry in self._entries.get(parent_type, tuple()):
                    entries.add(entry)
            return list(entries)
        return self._entries.get(key, [])

    def _filter_entries_by_attributes(
        self, key: Key, entries: Iterable[E]
    ) -> Iterable[E]:
        if self._attribute_filterer is None:
            return entries
        attributes = get_attributes(key)
        if attributes and (
            filtered := [
                entry
                for entry in entries
                if self._attribute_filterer.match_entry_attributes(
                    entry, attributes
                )
            ]
        ):
            return filtered
        return entries

    def get(self, key: Key) -> Iterable[E] | None:
        type_ = get_type(key)
        qualifiers = get_qualifiers(key)
        variance = resolve_variance(qualifiers, self._default_variance)

        entries: list[E] = self._get_entries(type_, variance)
        if not entries:
            return None

        return self._filter_entries_by_attributes(key, entries)
