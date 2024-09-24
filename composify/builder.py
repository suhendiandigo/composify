import asyncio
from typing import Any, Protocol, TypeVar

from composify.blueprint import Blueprint

__all__ = [
    "AsyncBuilder",
    "Builder",
]


T = TypeVar("T")


class BuilderSaveTo(Protocol):
    def __setitem__(self, key: type[Any], value: Any) -> None:
        raise NotImplementedError()


class AsyncBuilder:

    _cache: dict[Blueprint[Any], asyncio.Task[Any]]

    def __init__(
        self,
        save_to: BuilderSaveTo | None = None,
    ) -> None:
        self._cache = {}
        self._save_to = save_to

    async def from_blueprint(self, blueprint: Blueprint[T]) -> T:
        task = self._cache.get(blueprint, None)
        if task is not None:
            return await task
        task = asyncio.Task(self._from_blueprint(blueprint))

        # We cache the coroutine instead of the result
        # This allows asynchronous requests to share the same coroutine
        self._cache[blueprint] = task

        value = await task

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

        if asyncio.iscoroutinefunction(blueprint.constructor):
            return await blueprint.constructor(**parameters)  # type: ignore[misc]
        else:
            return blueprint.constructor(**parameters)  # type: ignore[return-value]


class Builder:

    _cache: dict[Blueprint[Any], Any]

    def __init__(
        self,
        save_to: BuilderSaveTo | None = None,
    ) -> None:
        self._cache = {}
        self._save_to = save_to

    def from_blueprint(self, blueprint: Blueprint[T]) -> T:
        value = self._cache.get(blueprint, None)
        if value is not None:
            return value

        value = self._from_blueprint(blueprint)

        self._cache[blueprint] = value

        if self._save_to is not None:
            self._save_to[blueprint.output_type] = value
        return value

    def _from_blueprint(self, blueprint: Blueprint[T]) -> T:
        parameters = {
            name: self.from_blueprint(param)
            for name, param in blueprint.dependencies
        }

        return blueprint.constructor(**parameters)
