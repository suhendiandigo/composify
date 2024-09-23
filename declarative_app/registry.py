from abc import ABC, abstractmethod
from asyncio import Protocol
from bisect import insort
from typing import Generic, Iterable, TypeAlias, TypeVar

from declarative_app.metadata.attributes import AttributeSet, get_attributes
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


class AttributeFilterer(Protocol):

    def filter_entries_by_attributes(
        self, entries: Iterable[Entry], attributes: AttributeSet
    ):
        raise NotImplementedError()


class DefaultAttributeFilterer(AttributeFilterer):

    def filter_entries_by_attributes(
        self, entries: Iterable[Entry], attributes: AttributeSet
    ):
        if attributes and (
            filtered := tuple(
                entry
                for entry in entries
                if entry.attributes.issuperset(attributes)
            )
        ):
            return filtered
        return entries


class UniqueEntryValidator(Protocol, Generic[E]):

    def validate_uniqueness(self, entry: E, others: Iterable[E]) -> None:
        raise NotImplementedError()


class DefaultUniqueEntryValidator(UniqueEntryValidator[E]):

    def validate_uniqueness(self, entry: E, others: Iterable[E]) -> None:
        for other in others:
            if entry == other:
                raise DuplicatedEntryError(entry, other)


_EMPTY_RESULT: tuple = tuple()


class TypedRegistry(Generic[E]):

    __slots__ = (
        "_entries",
        "_default_variance",
        "_attribute_filterer",
        "_unique_validator",
    )

    _entries: dict[Key, list[E]]

    def __init__(
        self,
        initial_entries: Iterable[E] | None = None,
        *,
        default_variance: VarianceType = "covariant",
        attribute_filterer: AttributeFilterer | None = None,
        unique_validator: UniqueEntryValidator | None = None,
    ) -> None:
        self._entries = {}
        self._default_variance = default_variance
        self._attribute_filterer = (
            attribute_filterer or DefaultAttributeFilterer()
        )
        self._unique_validator = (
            unique_validator or DefaultUniqueEntryValidator()
        )
        if initial_entries is not None:
            self.add_entries(initial_entries)

    def _validate_uniqueness(self, entry: E, others: Iterable[E]) -> None:
        self._unique_validator.validate_uniqueness(entry, others)

    def _add_entry(self, key: Key, entry: E) -> None:
        if key in self._entries:
            rules = self._entries[key]
            self._validate_uniqueness(entry, rules)
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

    def _remove_entry(self, key: Key, entry: E) -> None:
        if key in self._entries:
            rules = self._entries[key]
            rules.remove(entry)
            if not rules:
                del self._entries[key]

    def remove_entry(self, entry: E) -> None:
        for type_ in resolve_base_types(entry.key):
            self._remove_entry(type_, entry)

    def _get_entries(self, key: Key, variance: VarianceType) -> tuple[E, ...]:
        if variance == "invariant":
            return tuple(
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
            return tuple(entries)
        return tuple(self._entries.get(key, _EMPTY_RESULT))

    def _filter_entries_by_attributes(
        self, key: Key, entries: tuple[E, ...]
    ) -> tuple[E, ...]:
        if self._attribute_filterer is None:
            return entries
        return self._attribute_filterer.filter_entries_by_attributes(
            entries, attributes=get_attributes(key)
        )

    def get(self, key: Key) -> tuple[E, ...]:
        type_ = get_type(key)
        qualifiers = get_qualifiers(key)
        variance = resolve_variance(qualifiers, self._default_variance)

        entries: tuple[E, ...] = self._get_entries(type_, variance)
        if not entries:
            return _EMPTY_RESULT

        return self._filter_entries_by_attributes(key, entries)
