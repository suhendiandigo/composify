import sys
from typing import (
    Annotated,
    Any,
    Callable,
    TypeAlias,
    TypeVar,
    get_args,
    get_origin,
)

if sys.version_info < (3, 10):
    SLOTS = {}
else:
    SLOTS = {"slots": True}


class BaseMetadata:
    __slots__ = ()


M = TypeVar("M", bound=BaseMetadata)

TypeMetadataPair: TypeAlias = tuple[type, tuple[M, ...]]


def _get_metadata(
    type_: type, is_instance_func: Callable[[Any], bool]
) -> TypeMetadataPair:
    vals: tuple[Any, ...] = getattr(type_, "__metadata__", tuple())
    if not vals:
        return type_, vals
    origin = get_origin(type_)
    if origin is Annotated:
        type_ = get_args(type_)[0]
    return type_, tuple(filter(is_instance_func, vals))


def _is_base_metadata_instance(val: Any) -> bool:
    return isinstance(val, BaseMetadata)


def get_metadata(type_: type) -> TypeMetadataPair:
    return _get_metadata(type_, _is_base_metadata_instance)
