from dataclasses import dataclass
from typing import Generic, TypeVar

import pytest

from composify.errors import MissingReturnTypeAnnotation
from composify.rules import rule

T = TypeVar("T")


@dataclass(frozen=True)
class Base(Generic[T]):
    value: T


class Child(Base[int]):
    pass


class GenericChild(Base[T]):
    pass


def test_get_generic():
    with pytest.raises(MissingReturnTypeAnnotation):

        @rule
        def create_generic() -> Base[int]:
            pass


def test_get_child():
    @rule
    def create_child() -> Child:
        pass


def test_get_generic_child():
    with pytest.raises(MissingReturnTypeAnnotation):

        @rule
        def create_generic() -> GenericChild[int]:
            pass
