from collections.abc import Sequence
from dataclasses import dataclass
from types import NoneType, UnionType
from typing import Annotated, Any, get_args, get_origin

from composify.errors import InvalidTypeAnnotation


@dataclass(frozen=True)
class TypeInfo:
    annotation: Any
    inner_type: type
    is_optional: bool
    is_annotated: bool
    metadata: Sequence[Any]

    @property
    def __metadata__(self):
        return self.metadata


def ensure_type_annotation(
    *,
    type_annotation: Any,
    name: str,
    raise_type: type[InvalidTypeAnnotation] = InvalidTypeAnnotation,
) -> TypeInfo:
    if type_annotation is None:
        raise raise_type(f"{name} is missing a type annotation.")
    inner_type = type_annotation
    is_optional = False
    is_annotated = False
    metadata = []
    while not isinstance(inner_type, type):
        origin = get_origin(inner_type)
        if origin is UnionType:
            args = get_args(inner_type)
            is_optional = any(arg is NoneType for arg in args)
            union_types = tuple(filter(lambda x: x is not NoneType, args))
            if len(union_types) > 1:
                raise TypeError("Union type is not currently supported")
            inner_type = union_types[0]
        elif origin is Annotated:
            args = get_args(inner_type)
            inner_type = args[0]
            metadata.extend(args[1:])
            is_annotated = True
        else:
            raise raise_type(
                f"The annotation for {name} must be a type, got {type_annotation} of type {type(type_annotation)}."
            )
    return TypeInfo(
        annotation=type_annotation,
        inner_type=inner_type,
        is_optional=is_optional,
        is_annotated=is_annotated,
        metadata=tuple(metadata),
    )


def resolve_type_name(value: Any) -> str:
    """Resolve qualified name of a value."""
    return f"{value.__module__}.{value.__qualname__}".replace(".<locals>", "")
