from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TypeVar

from composify.blueprint import (
    DEFAULT_RESOLUTION_MODE,
    Blueprint,
    ResolutionMode,
)
from composify.errors import MultipleResolutionError, NoResolutionError
from composify.types import AnnotatedType

T = TypeVar("T")


def select_blueprint(type_: AnnotatedType[T], plans: tuple[Blueprint[T], ...]):
    if len(plans) > 1:
        raise MultipleResolutionError(type_, plans)
    elif len(plans) == 0:
        raise NoResolutionError(type_)
    return plans[0]


class GetOrCreate(ABC):
    @abstractmethod
    def one(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode = DEFAULT_RESOLUTION_MODE,
    ) -> T:
        raise NotImplementedError()

    @abstractmethod
    def all(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode = DEFAULT_RESOLUTION_MODE,
    ) -> Sequence[T]:
        raise NotImplementedError()


class AsyncGetOrCreate(ABC):
    @abstractmethod
    async def one(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode = DEFAULT_RESOLUTION_MODE,
    ) -> T:
        raise NotImplementedError()

    @abstractmethod
    async def all(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode = DEFAULT_RESOLUTION_MODE,
    ) -> Sequence[T]:
        raise NotImplementedError()
