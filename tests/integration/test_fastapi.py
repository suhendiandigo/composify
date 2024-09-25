import itertools
from contextlib import asynccontextmanager
from dataclasses import dataclass

import pytest
from fastapi import APIRouter

from composify import rule
from composify.applications import Composify
from composify.fastapi import (
    APIRouterCollection,
    LifespanHook,
    default_rules,
    router_rule,
)
from composify.fastapi.hooks import Lifespan
from composify.rules import as_rule, collect_rules


@dataclass(frozen=True)
class Prefix:
    prefix: str


@router_rule
def default_router() -> APIRouter:
    return APIRouter()


@router_rule
def example_router(prefix: Prefix) -> APIRouter:
    return APIRouter(prefix=prefix.prefix)


rules = collect_rules()


def test_router():
    composify = Composify(rules=itertools.chain(default_rules, rules))

    routers = composify.get_or_create(APIRouterCollection)

    assert len(routers) == 1


@rule
def default_prefix() -> Prefix:
    return Prefix("/default")


@rule
def unused_prefix() -> Prefix:
    return Prefix("/unused")


rules_2 = collect_rules()


def test_deduplicated_router():
    composify = Composify(rules=itertools.chain(default_rules, rules_2))

    routers = composify.get_or_create(APIRouterCollection)

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


@router_rule
def life_span_router(_: ExampleLifespan) -> APIRouter:
    return APIRouter()


@pytest.mark.asyncio_cooperative
async def test_router_lifespan():
    composify = Composify(
        rules=itertools.chain(
            default_rules, (as_rule(ExampleLifespan), as_rule(life_span_router))
        )
    )

    lifespan = composify.get_or_create(Lifespan)
    routers = composify.get_or_create(APIRouterCollection)
    lifespan_impl = composify.get_or_create(ExampleLifespan)

    assert len(routers) == 1

    async with lifespan(None):
        assert lifespan_impl.startup
    assert lifespan_impl.shutdown
