from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, ParamSpec, TypeAlias, TypeVar

from composify.rules import ParameterTypes

__all__ = [
    "Constructor",
]

T = TypeVar("T")
P = ParamSpec("P")


ConstructorFunction: TypeAlias = Callable[..., Awaitable[T]] | Callable[..., T]


@dataclass(frozen=True)
class Constructor(Generic[T]):
    source: str
    constructor: ConstructorFunction[T]
    is_async: bool
    output_type: type[T]
    dependencies: ParameterTypes
