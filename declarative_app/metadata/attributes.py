from .base import BaseMetadata, MetadataSet, _collect_metadata


class BaseAttributeMetadata(BaseMetadata):
    pass


class AttributeSet(MetadataSet[BaseAttributeMetadata]):
    pass


def collect_attributes(type_: type) -> AttributeSet:
    """Collect all annotated metadata that inherits BaseAttributeMetadata class as a frozenset."""
    return _collect_metadata(type_, BaseAttributeMetadata, AttributeSet)


class Name(str, BaseAttributeMetadata):

    def __repr__(self) -> str:
        return f"Name({self})"
