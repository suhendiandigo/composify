from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, ParamSpec, TypeAlias, TypeVar

from composify.rules import ParameterTypes
from composify.types import AnnotatedType

__all__ = [
    "Constructor",
]

T = TypeVar("T")
P = ParamSpec("P")


SyncConstructorFunction: TypeAlias = Callable[..., T]
AsyncConstructorFunction: TypeAlias = Callable[..., Awaitable[T]]
ConstructorFunction: TypeAlias = (
    SyncConstructorFunction[T] | AsyncConstructorFunction[T] | type
)


@dataclass(frozen=True)
class Constructor(Generic[T]):
    source: str
    constructor: ConstructorFunction[T]
    is_async: bool
    output_type: AnnotatedType
    dependencies: ParameterTypes
