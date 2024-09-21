import sys
from dataclasses import dataclass
from typing import Any

if sys.version_info < (3, 10):
    SLOTS = {}
else:
    SLOTS = {"slots": True}


class BaseMetadata:
    __slots__ = ()


@dataclass(frozen=True, **SLOTS)
class Name(BaseMetadata):
    name: str


def _is_metadata_instance(val: Any) -> bool:
    return isinstance(val, BaseMetadata)


def get_metadata(type_: type) -> tuple[BaseMetadata, ...]:
    vals: tuple[Any, ...] = getattr(type_, "__metadata__", tuple())
    if not vals:
        return vals
    return tuple(filter(_is_metadata_instance, vals))
