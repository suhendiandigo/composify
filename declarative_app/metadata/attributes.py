from dataclasses import dataclass
from typing import Any, TypeAlias

from .base import SLOTS, BaseMetadata, MetadataSet, _get_metadata


class BaseAttributeMetadata(BaseMetadata):
    pass


AttributeSet: TypeAlias = MetadataSet[BaseAttributeMetadata]


@dataclass(frozen=True, **SLOTS)
class Name(BaseAttributeMetadata):
    name: str


def _is_attribute_instance(val: Any) -> bool:
    return isinstance(val, BaseAttributeMetadata)


def get_attributes(type_: type) -> AttributeSet:
    return _get_metadata(type_, _is_attribute_instance)


def resolve_name(
    attributes: AttributeSet,
) -> str | None:
    for attribute in attributes:
        if isinstance(attribute, Name):
            return attribute.name
    return None
