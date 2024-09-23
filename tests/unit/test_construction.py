import asyncio

import pytest
from fixture.example_complex_rules import Param, Result, rules

from declarative_app.builder import Builder
from declarative_app.provider import ContainerInstanceProvider
from tests.utils import create_resolver, create_rule_plan_factory


@pytest.mark.asyncio_cooperative
async def test_construct(container):
    resolver = create_resolver(
        ContainerInstanceProvider(container),
        create_rule_plan_factory(*rules),
    )
    container.add(Param(5))
    plans = list(resolver.resolve(Result))
    builder = Builder()
    results = await asyncio.gather(
        *(builder.from_blueprint(plan) for plan in plans)
    )
    for result in results:
        assert isinstance(result, Result)


@pytest.mark.asyncio_cooperative
async def test_concurrent_construct(container):
    resolver = create_resolver(
        ContainerInstanceProvider(container),
        create_rule_plan_factory(*rules),
    )
    container.add(Param(5))
    plans = list(resolver.resolve(Result))
    builder = Builder()
    plan = plans[0]
    results = await asyncio.gather(
        *(builder.from_blueprint(plan) for _ in range(4))
    )
    for result in results:
        assert isinstance(result, Result)
        assert result == results[0]
        assert result.value == 25
