from dataclasses import dataclass
from typing import Any, TypeAlias

from .base import SLOTS, BaseMetadata, MetadataCollection, _get_metadata


class BaseAttributeMetadata(BaseMetadata):
    pass


AttributeCollection: TypeAlias = MetadataCollection[BaseAttributeMetadata]


@dataclass(frozen=True, **SLOTS)
class Name(BaseAttributeMetadata):
    name: str


def _is_attribute_instance(val: Any) -> bool:
    return isinstance(val, BaseAttributeMetadata)


def get_attributes(type_: type) -> AttributeCollection:
    return _get_metadata(type_, _is_attribute_instance)
