import itertools
from typing import (  # type: ignore[attr-defined]
    Annotated,
    Any,
    ForwardRef,
    Generic,
    Protocol,
    TypeAlias,
    TypeVar,
    Union,
    _AnnotatedAlias,
    _eval_type,
    get_args,
    get_origin,
)

from composify.errors import InvalidTypeAnnotation


def ensure_type_annotation(
    *,
    type_annotation: type | None,
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


def _expand_union_args_combinations(type_):
    if get_origin(type_) == Union:
        result = []
        args = get_args(type_)
        for comb in itertools.chain.from_iterable(
            itertools.combinations(args, n + 1) for n in range(0, len(args))
        ):
            result.append(comb)
        return tuple(result)
    return [type_]


def _expand_generic_args(type_) -> list[type]:
    origin = get_origin(type_)
    args = get_args(type_)
    if not args:
        return [type_]
    result = []
    for arg in itertools.chain.from_iterable(
        _expand_union_args_combinations(arg) for arg in args
    ):
        result.append(origin[arg])
    return result


def _resolve_bases(type_: type) -> set[type]:
    """Resolve all bases of a type including generic bases."""
    bases = set(type_.mro())
    if hasattr(type_, "__orig_bases__"):
        # See PEP 560: https://peps.python.org/pep-0560/#dynamic-class-creation-and-types-resolve-bases
        # For generics support
        orig_bases = type_.__orig_bases__
        for base in itertools.chain.from_iterable(
            _expand_generic_args(base) for base in orig_bases
        ):
            bases.add(base)

    return bases


EXCLUDED_BASE_TYPES = (object, Protocol, Generic)


def resolve_base_types(type_: type) -> tuple[type, ...]:
    return tuple(
        type_
        for type_ in _resolve_bases(type_)
        if type_ not in EXCLUDED_BASE_TYPES
    )


def resolve_forward_ref(forward_ref: str, globals_: dict):
    if not isinstance(forward_ref, str):
        return forward_ref

    return _eval_type(ForwardRef(forward_ref), globals_, globals_)


T = TypeVar("T")

AnnotatedType: TypeAlias = type[T] | _AnnotatedAlias


def get_type(type_: AnnotatedType) -> type:
    origin = get_origin(type_)
    if origin is Annotated:
        type_ = get_args(type_)[0]
    return type_


def resolve_type_name(value: Any):
    return f"{value.__module__}.{value.__qualname__}".replace(".<locals>", "")
