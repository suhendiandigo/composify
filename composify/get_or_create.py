from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TypeVar

from composify.blueprint import Blueprint, ResolutionMode
from composify.errors import MultipleResolutionError, NoResolutionError
from composify.types import AnnotatedType

T = TypeVar("T")


def select_blueprint(type_: AnnotatedType[T], plans: tuple[Blueprint[T], ...]):
    if len(plans) > 1:
        raise MultipleResolutionError(type_, plans)
    elif len(plans) == 0:
        raise NoResolutionError(type_)
    return plans[0]


class _DefaultResolution:
    def __init__(self, default_resolution: ResolutionMode) -> None:
        self._default_resolution = default_resolution

    def _resolution(
        self, resolution_mode: ResolutionMode | None
    ) -> ResolutionMode:
        return (
            self._default_resolution
            if resolution_mode is None
            else resolution_mode
        )


class GetOrCreate(ABC, _DefaultResolution):
    @abstractmethod
    def one(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> T:
        raise NotImplementedError()

    @abstractmethod
    def all(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> Sequence[T]:
        raise NotImplementedError()


class AsyncGetOrCreate(ABC, _DefaultResolution):
    @abstractmethod
    async def one(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> T:
        raise NotImplementedError()

    @abstractmethod
    async def all(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> Sequence[T]:
        raise NotImplementedError()
