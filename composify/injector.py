import asyncio
import inspect
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar, get_type_hints

from composify.errors import MissingParameterTypeAnnotation
from composify.getter import Getter
from composify.types import ensure_type_annotation

A = TypeVar("A", Any, Coroutine[Any, Any, Any])


class Injector:
    def __init__(self, getter: Getter) -> None:
        self._getter = getter

    def __call__(
        self,
        function: Callable[..., A],
        kwargs: dict[str, Any],
        exclude: set[str],
    ) -> Callable[[], A]:
        func_id = f"{function.__module__}:{function.__name__}"
        func_params = inspect.signature(function).parameters
        type_hints = get_type_hints(function, include_extras=True)

        parameters_to_inject = tuple(
            parameter
            for parameter in func_params
            if parameter not in kwargs and parameter not in exclude
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

            async def wrapper():
                names, coroutines = zip(
                    *(
                        (name, self._getter.aget(type_annotation))
                        for name, type_annotation in parameter_types
                    ),
                    strict=True,
                )
                return function(
                    **dict(
                        zip(
                            names,
                            await asyncio.gather(*coroutines),
                            strict=True,
                        )
                    ),
                    **kwargs,
                )
        else:

            def wrapper():
                parameters = {
                    name: self._getter.get(type_annotation)
                    for name, type_annotation in parameter_types
                }
                return function(**parameters, **kwargs)

        return wrapper
