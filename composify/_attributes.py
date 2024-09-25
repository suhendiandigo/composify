from dataclasses import dataclass

from composify.metadata.attributes import BaseAttributeMetadata


@dataclass(frozen=True, slots=True)
class ProvidedBy(BaseAttributeMetadata):
    """Describe the provider of the value."""

    source: str


class Name(str, BaseAttributeMetadata):
    def __repr__(self) -> str:
        return f"Name({self})"
