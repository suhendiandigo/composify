"""Implementation of Attributes."""

from composify.types import AnnotatedType

from .base import BaseMetadata, MetadataSet, _collect_metadata


class BaseAttributeMetadata(BaseMetadata):
    """Base class for all attributes."""

    pass


class AttributeSet(MetadataSet[BaseAttributeMetadata]):
    """A frozenset of Attributes."""

    pass


def collect_attributes(type_: AnnotatedType) -> AttributeSet:
    """Collect all BaseAttributeMetadata class.

    Args:
        type_ (AnnotatedType): The type annotated with attributes.

    Returns:
        AttributeSet: Set of attributes.
    """
    return _collect_metadata(type_, BaseAttributeMetadata, AttributeSet)
