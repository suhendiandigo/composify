from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Literal, TypeAlias, TypeVar

from composify.blueprint import Blueprint
from composify.errors import MultipleResolutionError, NoResolutionError
from composify.types import AnnotatedType

T = TypeVar("T")
ResolutionMode: TypeAlias = Literal["default", "select_first"]


def default_select_blueprint(
    type_: AnnotatedType[T], plans: tuple[Blueprint[T], ...]
) -> Blueprint[T]:
    if len(plans) > 1:
        raise MultipleResolutionError(type_, plans)
    elif len(plans) == 0:
        raise NoResolutionError(type_)
    return plans[0]


def select_first_blueprint(
    type_: AnnotatedType[T], plans: tuple[Blueprint[T], ...]
) -> Blueprint[T]:
    if len(plans) == 0:
        raise NoResolutionError(type_)
    return plans[0]


def blueprint_selector(resolution_mode: ResolutionMode = "default"):
    match resolution_mode:
        case "select_first":
            return select_first_blueprint
        case _:
            return default_select_blueprint


class GetOrCreate(ABC):
    @abstractmethod
    def one(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode = "default",
    ) -> T:
        raise NotImplementedError()

    @abstractmethod
    def all(self, type_: AnnotatedType[T]) -> Sequence[T]:
        raise NotImplementedError()


class AsyncGetOrCreate(ABC):
    @abstractmethod
    async def one(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode = "default",
    ) -> T:
        raise NotImplementedError()

    @abstractmethod
    async def all(self, type_: AnnotatedType[T]) -> Sequence[T]:
        raise NotImplementedError()
