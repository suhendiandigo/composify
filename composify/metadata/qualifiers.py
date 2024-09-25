"""Implementation of Qualifiers."""

from composify.types import AnnotatedType

from .base import BaseMetadata, MetadataSet, _collect_metadata


class BaseQualifierMetadata(BaseMetadata):
    """Base class for all qualifiers."""

    pass


class QualifierSet(MetadataSet[BaseQualifierMetadata]):
    """A frozenset of Qualifiers."""

    pass


def collect_qualifiers(type_: AnnotatedType) -> QualifierSet:
    """Collect all BaseQualifierMetadata class.

    Args:
        type_ (AnnotatedType): The type annotated with qualifiers.

    Returns:
        QualifierSet: Set of qualifiers.
    """
    return _collect_metadata(type_, BaseQualifierMetadata, QualifierSet)
