"""Protocol for GetOrCreate operations.

Example:
    from typing import Annotated
    from composify import Composify, rule, collect_rules
    from composify.qualifiers import Exhaustive
    from composify.resolutions import EXHAUSTIVE


    class A(int):
        pass

    @rule
    def a_value_1() -> A:
        return 1

    @rule
    def a_value_2() -> A:
        return 2


    composify = Composify(rules=collect_rules())

    results = composify.get_or_create_all(A)

    print(results)
    #> (1,)

    results = composify.get_or_create_all(Annotated[A, Exhaustive])
    # also equivalent to
    results = composify.get_or_create_all(A, EXHAUSTIVE)

    print(results)
    #> (1,2)

"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TypeVar

from composify.blueprint import ResolutionMode
from composify.types import AnnotatedType

T = TypeVar("T")


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
    """Synchronous Get or Create protocol. Only support non async @rule."""

    @abstractmethod
    def one(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> T:
        """Get one instance of T.

        Args:
            type_ (AnnotatedType[T]): The type to get.
            resolution_mode (ResolutionMode | None, optional): How the dependency graph is resolved. Defaults to select_first.

        Returns:
            T: An instance of T

        Raises:
            InvalidResolutionModeError: Raised if the resolution mode is invalid.
            ResolutionFailureError: Raised if there is no generated blueprint.
        """
        raise NotImplementedError()

    @abstractmethod
    def all(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> Sequence[T]:
        """Get all instance of T.

        Args:
            type_ (AnnotatedType[T]): The type to get.
            resolution_mode (ResolutionMode | None, optional): How the dependency graph is resolved. Defaults to select_first.

        Returns:
            Sequence[T]: All instances of T.

        Raises:
            InvalidResolutionModeError: Raised if the resolution mode is invalid.
        """
        raise NotImplementedError()


class AsyncGetOrCreate(ABC, _DefaultResolution):
    """Asynchronous Get or Create protocol."""

    @abstractmethod
    async def one(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> T:
        """Get one instance of T.

        Args:
            type_ (AnnotatedType[T]): The type to get.
            resolution_mode (ResolutionMode | None, optional): How the dependency graph is resolved. Defaults to select_first.

        Returns:
            T: An instance of T

        Raises:
            InvalidResolutionModeError: Raised if the resolution mode is invalid.
            ResolutionFailureError: Raised if there is no generated blueprint.
        """
        raise NotImplementedError()

    @abstractmethod
    async def all(
        self,
        type_: AnnotatedType[T],
        resolution_mode: ResolutionMode | None = None,
    ) -> Sequence[T]:
        """Get all instance of T.

        Args:
            type_ (AnnotatedType[T]): The type to get.
            resolution_mode (ResolutionMode | None, optional): How the dependency graph is resolved. Defaults to select_first.

        Returns:
            Sequence[T]: All instances of T.

        Raises:
            InvalidResolutionModeError: Raised if the resolution mode is invalid.
        """
        raise NotImplementedError()
