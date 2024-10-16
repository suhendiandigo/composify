"""Module for base metadata implementation."""

from .attributes import AttributeSet, BaseAttributeMetadata, collect_attributes
from .base import BaseMetadata, MetadataSet, collect_metadata
from .qualifiers import BaseQualifierMetadata, QualifierSet, collect_qualifiers

__all__ = [
    "BaseMetadata",
    "MetadataSet",
    "collect_metadata",
    "BaseAttributeMetadata",
    "AttributeSet",
    "collect_attributes",
    "Name",
    "BaseQualifierMetadata",
    "QualifierSet",
    "collect_qualifiers",
    "DisallowSubclass",
]
