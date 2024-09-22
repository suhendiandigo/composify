import sys
from typing import Any, Callable, TypeAlias, TypeVar

if sys.version_info < (3, 10):
    SLOTS = {}
else:
    SLOTS = {"slots": True}


class BaseMetadata:
    __slots__ = ()


M = TypeVar("M", bound=BaseMetadata)

MetadataSet: TypeAlias = frozenset[M]


def _get_metadata(
    type_: type, is_instance_func: Callable[[Any], bool]
) -> MetadataSet:
    vals: tuple[Any, ...] = getattr(type_, "__metadata__", tuple())
    if not vals:
        return frozenset(vals)
    return frozenset(filter(is_instance_func, vals))


def _is_base_metadata_instance(val: Any) -> bool:
    return isinstance(val, BaseMetadata)


def get_metadata(type_: type) -> MetadataSet:
    return _get_metadata(type_, _is_base_metadata_instance)
