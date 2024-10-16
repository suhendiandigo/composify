import itertools
from contextlib import asynccontextmanager
from dataclasses import dataclass

import pytest
from fastapi import APIRouter

from composify import rule
from composify.applications import Composify
from composify.errors import (
    MultipleDependencyResolutionError,
    ResolutionFailureError,
)
from composify.fastapi import APIRouterCollection, LifespanHook, default_rules
from composify.fastapi.lifespan import Lifespan
from composify.rules import as_rule, collect_rules


@dataclass(frozen=True)
class Prefix:
    prefix: str


@rule
def default_router() -> APIRouter:
    return APIRouter()


@rule
def example_router(prefix: Prefix) -> APIRouter:
    return APIRouter(prefix=prefix.prefix)


rules = collect_rules()


def test_router():
    composify = Composify(rules=itertools.chain(default_rules, rules))

    routers = composify.get_or_create.one(APIRouterCollection)

    assert len(routers) == 1


@rule
def default_prefix() -> Prefix:
    return Prefix("/default")


rules_2 = collect_rules()


def test_get_multiple_routers():
    composify = Composify(rules=itertools.chain(default_rules, rules_2))

    routers = composify.get_or_create.one(APIRouterCollection)

    assert len(routers) == 2
    assert routers[0].prefix == ""
    assert routers[1].prefix == "/default"


@rule
class ExampleLifespan(LifespanHook):
    def __init__(self) -> None:
        super().__init__()
        self.startup = False
        self.shutdown = False

    @asynccontextmanager
    async def on_lifespan(self):
        self.startup = True
        yield
        self.shutdown = True


@rule
def life_span_router(_: ExampleLifespan) -> APIRouter:
    return APIRouter()


@pytest.mark.asyncio_cooperative
async def test_router_lifespan():
    composify = Composify(
        rules=itertools.chain(
            default_rules, (as_rule(ExampleLifespan), as_rule(life_span_router))
        )
    )

    lifespan = composify.get_or_create.one(Lifespan)
    routers = composify.get_or_create.one(APIRouterCollection)
    lifespan_impl = composify.get_or_create.one(ExampleLifespan)

    assert len(routers) == 1

    async with lifespan(None):
        assert lifespan_impl.startup
    assert lifespan_impl.shutdown


@rule
def unused_prefix() -> Prefix:
    return Prefix("/unused")


rules_3 = collect_rules()


def test_error_for_permutations():
    composify = Composify(rules=itertools.chain(default_rules, rules_3))

    with pytest.raises(ResolutionFailureError) as exc:
        composify.get_or_create.one(APIRouterCollection)
    assert exc.value.contains(MultipleDependencyResolutionError)
