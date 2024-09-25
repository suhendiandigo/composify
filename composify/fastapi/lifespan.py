"""Support for FastAPI lifespan."""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from contextlib import (
    AbstractAsyncContextManager,
    AsyncExitStack,
    asynccontextmanager,
)

from fastapi import FastAPI


class LifespanHook(ABC):
    """Implement on_lifespan hook to join FastAPI lifespan."""

    @abstractmethod
    @asynccontextmanager
    async def on_lifespan(self, *args, **kwargs):
        """The lifespan context manager."""
        pass


class Lifespan:
    """The lifespan context manager for invoking all implementor of LifespanHook."""

    def __init__(
        self, hooks: Sequence[Callable[[], AbstractAsyncContextManager[None]]]
    ) -> None:
        self._hooks = hooks

    @property
    def hooks(
        self,
    ) -> Sequence[Callable[[], AbstractAsyncContextManager[None]]]:
        """All injected hooks."""
        return self._hooks

    @asynccontextmanager
    async def __call__(self, _: FastAPI):
        """Invoke all context manager as a group."""
        async with AsyncExitStack() as stack:
            await asyncio.gather(
                *(stack.enter_async_context(hook()) for hook in self.hooks)
            )
            yield
