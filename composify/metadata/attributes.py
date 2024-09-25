from composify.types import AnnotatedType

from .base import BaseMetadata, MetadataSet, _collect_metadata


class BaseAttributeMetadata(BaseMetadata):
    pass


class AttributeSet(MetadataSet[BaseAttributeMetadata]):
    pass


def collect_attributes(type_: AnnotatedType) -> AttributeSet:
    """Collect all annotated metadata that inherits BaseAttributeMetadata class as a frozenset."""
    return _collect_metadata(type_, BaseAttributeMetadata, AttributeSet)
