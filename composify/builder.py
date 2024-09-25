"""Implementation of Builder and AsyncBuilder to build using blueprint."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Annotated, Any, Protocol, TypeVar, cast

from composify.attributes import ProvidedBy
from composify.blueprint import Blueprint
from composify.constructor import SyncConstructorFunction
from composify.errors import AsyncBlueprintError

__all__ = [
    "AsyncBuilder",
    "Builder",
]


T = TypeVar("T")


def _set_provider(value: Any, source: str):
    return Annotated[type(value), ProvidedBy(source)]


class BuilderSaveTo(Protocol):
    """Protocol to persist builder's result."""

    def __setitem__(self, key: type[Any], value: Any) -> None:
        raise NotImplementedError()


class AsyncBuilder:
    """Builder objects from blueprints. Supports async blueprints."""

    _cache: dict[Blueprint[Any], asyncio.Task[Any]]

    def __init__(
        self,
        save_to: BuilderSaveTo | None = None,
        threadpool_executor: ThreadPoolExecutor | None = None,
    ) -> None:
        self._cache = {}
        self._save_to = save_to
        self._threadpool_executor = threadpool_executor or ThreadPoolExecutor()

    async def get_cached(self, blueprint: Blueprint[T]) -> T | None:
        """Get cached value for a blueprint.

        Args:
            blueprint (Blueprint[T]): The blueprint cache to find.

        Returns:
            T | None: The cached value if it exists; otherwise None.
        """
        cached = self._cache.get(blueprint, None)
        return await cached if cached else None

    async def from_blueprint(self, blueprint: Blueprint[T]) -> T:
        """Build an object using a blueprint.

        Args:
            blueprint (Blueprint[T]): A blueprint to base on.

        Returns:
            T: A built object.
        """
        task = self._cache.get(blueprint, None)
        if task is not None:
            return await task
        task = asyncio.Task(self._from_blueprint(blueprint))

        # We cache the coroutine instead of the result
        # This allows asynchronous requests to share the same coroutine
        self._cache[blueprint] = task

        value = await task

        if self._save_to is not None:
            self._save_to[_set_provider(value, blueprint.source)] = value
        return value

    async def _from_blueprint(self, blueprint: Blueprint[T]) -> T:
        name_task_pairs = tuple(
            (name, self.from_blueprint(param))
            for name, param in blueprint.dependencies
        )

        names = tuple(p[0] for p in name_task_pairs)
        tasks = tuple(p[1] for p in name_task_pairs)

        results = tuple(await asyncio.gather(*tasks))

        parameters = dict(zip(names, results, strict=True))

        if asyncio.iscoroutinefunction(blueprint.constructor):
            return await blueprint.constructor(**parameters)
        else:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                self._threadpool_executor,
                partial(blueprint.constructor, **parameters),  # type: ignore[arg-type]
            )


class Builder:
    """Builder objects from blueprints. Does not support async blueprints."""

    _cache: dict[Blueprint[Any], Any]

    def __init__(
        self,
        save_to: BuilderSaveTo | None = None,
    ) -> None:
        self._cache = {}
        self._save_to = save_to

    def from_blueprint(self, blueprint: Blueprint[T]) -> T:
        """Build an object using a blueprint.

        Args:
            blueprint (Blueprint[T]): A blueprint to base on.

        Raises:
            AsyncBlueprintError: If the blueprint requires async loop.

        Returns:
            T: A built object.
        """
        if blueprint.is_async:
            raise AsyncBlueprintError(
                f"Trying to build from async blueprint {blueprint}"
            )
        value = self._cache.get(blueprint, None)
        if value is not None:
            return value

        value = self._from_blueprint(blueprint)

        self._cache[blueprint] = value

        if self._save_to is not None:
            self._save_to[_set_provider(value, blueprint.source)] = value
        return value

    def _from_blueprint(self, blueprint: Blueprint[T]) -> T:
        parameters = {
            name: self.from_blueprint(param)
            for name, param in blueprint.dependencies
        }

        return cast(SyncConstructorFunction, blueprint.constructor)(
            **parameters
        )
