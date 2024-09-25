from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Literal, TypeAlias, TypeVar

from composify.types import AnnotatedType

T = TypeVar("T")
ResolutionMode: TypeAlias = Literal["default", "select_first"]


class Getter(ABC):
    @abstractmethod
    async def aget(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode = "default",
    ) -> T:
        raise NotImplementedError()

    @abstractmethod
    async def aget_all(self, type_: AnnotatedType[T]) -> Iterable[T]:
        raise NotImplementedError()

    @abstractmethod
    def get(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode = "default",
    ) -> T:
        raise NotImplementedError()

    @abstractmethod
    def get_all(self, type_: AnnotatedType[T]) -> Iterable[T]:
        raise NotImplementedError()
