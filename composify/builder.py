import asyncio
from typing import Any, Protocol, TypeVar

from composify.blueprint import Blueprint

__all__ = [
    "Builder",
    "BuilderCache",
    "BuilderSaveTo",
]


T = TypeVar("T")


class BuilderCache(Protocol[T]):
    def __setitem__(self, key: Blueprint, value: T) -> None:
        raise NotImplementedError()

    def __getitem__(self, item: Blueprint) -> T:
        raise NotImplementedError()

    def get(self, key: Blueprint, default: T, /) -> T:
        raise NotImplementedError()


class BuilderSaveTo(Protocol):
    def __setitem__(self, key: type[Any], value: Any) -> None:
        raise NotImplementedError()


_undefined = object()


class Builder:

    _cache: BuilderCache[Any] | None

    def __init__(
        self,
        cache: BuilderCache | None = _undefined,  # type: ignore[assignment]
        save_to: BuilderSaveTo | None = None,
    ) -> None:
        self._cache = {} if cache is _undefined else cache
        self._save_to = save_to

    async def from_blueprint(self, blueprint: Blueprint[T]) -> T:
        if self._cache is not None:
            value = self._cache.get(blueprint, None)
            if value is not None:
                return await value
        coroutine = asyncio.Task(self._from_blueprint(blueprint))
        if self._cache is not None:
            # We cache the coroutine instead of the result
            # This allows asynchronous requests to share the same coroutine
            self._cache[blueprint] = coroutine
        value = await coroutine
        if self._save_to is not None:
            self._save_to[blueprint.output_type] = value
        return value

    async def _from_blueprint(self, blueprint: Blueprint[T]) -> T:
        parameter_name_coroutines = tuple(
            (name, self.from_blueprint(param))
            for name, param in blueprint.dependencies
        )

        names = tuple(p[0] for p in parameter_name_coroutines)
        coroutines = tuple(p[1] for p in parameter_name_coroutines)

        results = tuple(await asyncio.gather(*coroutines))

        parameters = {name: result for name, result in zip(names, results)}

        if blueprint.is_async:
            return await blueprint.constructor(**parameters)  # type: ignore[misc]
        else:
            return blueprint.constructor(**parameters)  # type: ignore[return-value]
