"""Support for dependency injection as a decorator."""

import asyncio
import inspect
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar, get_type_hints

from composify._helper import ensure_type_annotation
from composify.errors import MissingParameterTypeAnnotation
from composify.get_or_create import AsyncGetOrCreate, GetOrCreate

A = TypeVar("A", Any, Coroutine[Any, Any, Any])


def _resolve_parameters(
    function: Callable[..., A],
    params: dict[str, Any] | None = None,
    exclude: set[str] | None = None,
):
    func_id = f"{function.__module__}:{function.__name__}"
    func_params = inspect.signature(function).parameters
    type_hints = get_type_hints(function, include_extras=True)
    to_exclude = exclude or set()
    if params:
        to_exclude.union(params)

    parameters_to_inject = tuple(
        parameter for parameter in func_params if parameter not in to_exclude
    )

    parameter_types = tuple(
        (
            parameter,
            ensure_type_annotation(
                type_annotation=type_hints.get(parameter),
                name=f"{func_id} parameter {parameter}",
                raise_type=MissingParameterTypeAnnotation,
            ).annotation,
        )
        for parameter in parameters_to_inject
    )

    return parameter_types


class Injector:
    """This class provides the functionality to auto-wire a function."""

    def __init__(self, get_or_create: GetOrCreate) -> None:
        self._get_or_create = get_or_create

    def __call__(
        self,
        function: Callable[..., A],
        params: dict[str, Any] | None = None,
        exclude: set[str] | None = None,
    ) -> Callable[..., A]:
        """Wraps a function a supply its parameter using GetOrCreate.

        Args:
            function (Callable[..., A]): The function to decorate.
            params (dict[str, Any] | None, optional): Additional parameters. Defaults to None.
            exclude (set[str] | None, optional): Parameters to exclude from injection. Defaults to None.

        Returns:
            Callable[..., A]: An auto-wired function.

        Raises:
            MissingParameterTypeAnnotation: Raised if there are any missing type annotation.

        """
        parameter_types = _resolve_parameters(
            function=function, params=params, exclude=exclude
        )

        parameters: dict = {
            name: self._get_or_create.one(type_annotation)
            for name, type_annotation in parameter_types
        }

        del parameter_types, exclude

        @wraps(function)
        def wrapper(*args, **kwargs):
            if params:
                parameters.update(params)
            if kwargs:
                parameters.update(kwargs)
            return function(*args, **parameters)

        return wrapper


class AsyncInjector:
    """This class provides the functionality to auto-wire a function using async resolution."""

    def __init__(self, async_get_or_create: AsyncGetOrCreate) -> None:
        self._async_get_or_create = async_get_or_create

    async def __call__(
        self,
        function: Callable[..., A],
        params: dict[str, Any] | None = None,
        exclude: set[str] | None = None,
    ) -> Callable[..., A]:
        """Wraps a function a supply its parameter using AsyncGetOrCreate.

        Args:
            function (Callable[..., A]): The function to decorate.
            params (dict[str, Any] | None, optional): Additional parameters. Defaults to None.
            exclude (set[str] | None, optional): Parameters to exclude from injection. Defaults to None.

        Returns:
            Callable[..., A]: An auto-wired function.

        Raises:
            MissingParameterTypeAnnotation: Raised if there are any missing type annotation.

        """
        parameter_types = _resolve_parameters(
            function=function, params=params, exclude=exclude
        )

        names, coroutines = zip(
            *(
                (name, self._async_get_or_create.one(type_annotation))
                for name, type_annotation in parameter_types
            ),
            strict=True,
        )
        parameters = dict(
            zip(
                names,
                await asyncio.gather(*coroutines),
                strict=True,
            )
        )

        del parameter_types, exclude

        @wraps(function)
        def wrapper(*args, **kwargs):
            if params:
                parameters.update(params)
            if kwargs:
                parameters.update(kwargs)
            return function(*args, **parameters)

        return wrapper
