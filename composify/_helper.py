from collections.abc import Sequence
from dataclasses import dataclass
from types import NoneType, UnionType
from typing import Annotated, Any, _AnnotatedAlias, get_args, get_origin

from composify.errors import InvalidTypeAnnotation


@dataclass(frozen=True)
class GenericInfo:
    origin: type
    args: Sequence[type]


@dataclass(frozen=True)
class TypeInfo:
    annotation: Any
    inner_type: type
    is_optional: bool
    is_annotated: bool
    metadata: Sequence[Any]
    generic: GenericInfo | None = None

    @property
    def __metadata__(self):
        return self.metadata

    @property
    def is_generic(self):
        return self.generic is not None


def get_type_info(type_annotation: Any) -> TypeInfo:
    inner_type = type_annotation
    is_optional = False
    is_annotated = False
    generic = None
    metadata: list = []
    while not isinstance(inner_type, type):
        origin = get_origin(inner_type)
        args = get_args(inner_type)
        if origin is UnionType:
            is_optional = any(arg is NoneType for arg in args)
            union_types = tuple(filter(lambda x: x is not NoneType, args))
            if len(union_types) > 1:
                raise TypeError("Union type is not currently supported")
            inner_type = union_types[0]
        elif origin is Annotated:
            inner_type = args[0]
            metadata.extend(args[1:])
            is_annotated = True
        else:
            if inner_type == origin:
                break
            generic = GenericInfo(origin, args)
            inner_type = origin
    return TypeInfo(
        annotation=type_annotation,
        inner_type=inner_type,
        is_optional=is_optional,
        is_annotated=is_annotated,
        generic=generic,
        metadata=tuple(metadata),
    )


def wrap_metadata(type_: type, metadata: Sequence[Any]) -> type:
    return _AnnotatedAlias(type_, metadata)


def ensure_type_annotation(
    *,
    type_annotation: Any,
    name: str,
    raise_type: type[InvalidTypeAnnotation] = InvalidTypeAnnotation,
) -> TypeInfo:
    if type_annotation is None:
        raise raise_type(f"{name} is missing a type annotation.")
    return get_type_info(type_annotation)


def resolve_type_name(value: Any) -> str:
    """Resolve qualified name of a value."""
    return f"{value.__module__}.{value.__qualname__}".replace(".<locals>", "")
