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


class Injector:
    """This class provides the functionality to auto-wire a function."""

    def __init__(
        self, get_or_create: GetOrCreate, async_get_or_create: AsyncGetOrCreate
    ) -> None:
        self._get_or_create = get_or_create
        self._async_get_or_create = async_get_or_create

    def __call__(
        self,
        function: Callable[..., A],
        params: dict[str, Any] | None = None,
        exclude: set[str] | None = None,
    ) -> Callable[..., A]:
        """Wraps a function a supply its parameter using GetOrCreate.

        Args:
            function (Callable[..., A]): The function to wrap.
            params (dict[str, Any] | None, optional): Additional parameters. Defaults to None.
            exclude (set[str] | None, optional): Parameters to exclude from injection. Defaults to None.

        Returns:
            Callable[..., A]: An auto-wired function.
        """
        func_id = f"{function.__module__}:{function.__name__}"
        func_params = inspect.signature(function).parameters
        type_hints = get_type_hints(function, include_extras=True)
        to_exclude = exclude or set()
        if params:
            to_exclude.union(params)

        parameters_to_inject = tuple(
            parameter
            for parameter in func_params
            if parameter not in to_exclude
        )

        parameter_types = tuple(
            (
                parameter,
                ensure_type_annotation(
                    type_annotation=type_hints.get(parameter),
                    name=f"{func_id} parameter {parameter}",
                    raise_type=MissingParameterTypeAnnotation,
                ),
            )
            for parameter in parameters_to_inject
        )

        del func_id, func_params, type_hints, parameters_to_inject

        if asyncio.iscoroutinefunction(function):

            @wraps(function)
            async def wrapper(*args, **kwargs):
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
                if params:
                    parameters.update(params)
                if kwargs:
                    parameters.update(kwargs)
                return function(*args, **parameters)
        else:

            @wraps(function)
            def wrapper(*args, **kwargs):
                parameters = {
                    name: self._get_or_create.one(type_annotation)
                    for name, type_annotation in parameter_types
                }
                if params:
                    parameters.update(params)
                if kwargs:
                    parameters.update(kwargs)
                return function(*args, **parameters)

        return wrapper
