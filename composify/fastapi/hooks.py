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
    @abstractmethod
    @asynccontextmanager
    async def on_lifespan(self, *args, **kwargs):
        pass


class Lifespan:
    def __init__(
        self, hooks: Sequence[Callable[[], AbstractAsyncContextManager[None]]]
    ) -> None:
        self._hooks = hooks

    @property
    def hooks(
        self,
    ) -> Sequence[Callable[[], AbstractAsyncContextManager[None]]]:
        return self._hooks

    @asynccontextmanager
    async def __call__(self, _: FastAPI):
        async with AsyncExitStack() as stack:
            await asyncio.gather(
                *(stack.enter_async_context(hook()) for hook in self.hooks)
            )
            yield
