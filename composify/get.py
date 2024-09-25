from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TypeVar

from composify.types import AnnotatedType

T = TypeVar("T")


class Get(ABC):
    @abstractmethod
    def one(
        self,
        type_: AnnotatedType[T],
    ) -> T:
        raise NotImplementedError()

    @abstractmethod
    def all(self, type_: AnnotatedType[T]) -> Sequence[T]:
        raise NotImplementedError()
