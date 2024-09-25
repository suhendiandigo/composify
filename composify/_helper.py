from typing import Annotated, Any, get_origin

from composify.errors import InvalidTypeAnnotation


def ensure_type_annotation(
    *,
    type_annotation: Any,
    name: str,
    raise_type: type[InvalidTypeAnnotation],
) -> type:
    if type_annotation is None:
        raise raise_type(f"{name} is missing a type annotation.")
    if not isinstance(type_annotation, type):
        origin = get_origin(type_annotation)
        if origin is not Annotated:
            raise raise_type(
                f"The annotation for {name} must be a type, got {type_annotation} of type {type(type_annotation)}."
            )
    return type_annotation


def resolve_type_name(value: Any) -> str:
    """Resolve qualified name of a value."""
    return f"{value.__module__}.{value.__qualname__}".replace(".<locals>", "")
