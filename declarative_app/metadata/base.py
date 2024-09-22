import sys
from typing import Any, Callable, TypeAlias, TypeVar

if sys.version_info < (3, 10):
    SLOTS = {}
else:
    SLOTS = {"slots": True}


class BaseMetadata:
    __slots__ = ()


M = TypeVar("M", bound=BaseMetadata)

MetadataCollection: TypeAlias = tuple[M, ...]


def _get_metadata(
    type_: type, is_instance_func: Callable[[Any], bool]
) -> MetadataCollection:
    vals: tuple[Any, ...] = getattr(type_, "__metadata__", tuple())
    if not vals:
        return vals
    return tuple(filter(is_instance_func, vals))


def _is_base_metadata_instance(val: Any) -> bool:
    return isinstance(val, BaseMetadata)


def get_metadata(type_: type) -> MetadataCollection:
    return _get_metadata(type_, _is_base_metadata_instance)
