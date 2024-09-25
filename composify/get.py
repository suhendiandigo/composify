"""Protocol for Get operations."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TypeVar

from composify.types import AnnotatedType

T = TypeVar("T")


class Get(ABC):
    """Getter protocol. This protocols allows for retrieval of instances that
    has previously been created via Builder or AsyncBuilder.
    """

    @abstractmethod
    def one(
        self,
        type_: AnnotatedType[T],
    ) -> T:
        """Get an existing object of type.

        Args:
            type_ (AnnotatedType[T]): The type of the object to retrieve.

        Returns:
            T: An existing instance of T.
        """
        raise NotImplementedError()

    @abstractmethod
    def all(self, type_: AnnotatedType[T]) -> Sequence[T]:
        """Get all existing objects of type.

        Args:
            type_ (AnnotatedType[T]): The type of the objects to retrieve.

        Returns:
            Sequence[T]: All existing instances of T.
        """
        raise NotImplementedError()
