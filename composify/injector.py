import asyncio
import inspect
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar, get_type_hints

from composify.errors import MissingParameterTypeAnnotation
from composify.get import Get
from composify.types import ensure_type_annotation

A = TypeVar("A", Any, Coroutine[Any, Any, Any])


class Injector:
    def __init__(self, getter: Get) -> None:
        self._getter = getter

    def __call__(
        self,
        function: Callable[..., A],
        params: dict[str, Any] | None = None,
        exclude: set[str] | None = None,
    ) -> Callable[[], A]:
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
                        (name, self._getter.aget(type_annotation))
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
                    name: self._getter.one(type_annotation)
                    for name, type_annotation in parameter_types
                }
                if params:
                    parameters.update(params)
                if kwargs:
                    parameters.update(kwargs)
                return function(*args, **parameters)

        return wrapper
