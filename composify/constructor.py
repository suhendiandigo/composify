from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, TypeVar

from typing_extensions import ParamSpec, TypeAlias, _AnnotatedAlias

from composify.rules import ParameterTypes

__all__ = [
    "Constructor",
]

T = TypeVar("T")
P = ParamSpec("P")


SyncConstructorFunction: TypeAlias = Callable[..., T]
AsyncConstructorFunction: TypeAlias = Callable[..., Awaitable[T]]
ConstructorFunction: TypeAlias = (
    SyncConstructorFunction[T] | AsyncConstructorFunction[T]
)


@dataclass(frozen=True)
class Constructor(Generic[T]):
    source: str
    constructor: ConstructorFunction[T]
    is_async: bool
    output_type: type[T] | _AnnotatedAlias
    dependencies: ParameterTypes
