from composify.types import AnnotatedType

from .base import BaseMetadata, MetadataSet, _collect_metadata


class BaseQualifierMetadata(BaseMetadata):
    pass


class QualifierSet(MetadataSet[BaseQualifierMetadata]):
    pass


def collect_qualifiers(type_: AnnotatedType) -> QualifierSet:
    """Collect all annotated metadata that inherits BaseQualifierMetadata class as a frozenset."""
    return _collect_metadata(type_, BaseQualifierMetadata, QualifierSet)
