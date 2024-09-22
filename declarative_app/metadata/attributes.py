from dataclasses import dataclass
from typing import Any, TypeAlias

from .base import SLOTS, BaseMetadata, TypeMetadataPair, _get_metadata


class BaseAttributeMetadata(BaseMetadata):
    pass


TypeAttributePair: TypeAlias = TypeMetadataPair[BaseAttributeMetadata]


@dataclass(frozen=True, **SLOTS)
class Name(BaseAttributeMetadata):
    name: str


def _is_attribute_instance(val: Any) -> bool:
    return isinstance(val, BaseAttributeMetadata)


def get_attributes(type_: type) -> TypeAttributePair:
    return _get_metadata(type_, _is_attribute_instance)
