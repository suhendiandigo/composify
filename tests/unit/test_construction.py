import asyncio

import pytest
from fixture.example_complex_rules import Param, Result, rules

from declarative_app.construction import (
    ConstructionResolver,
    Constructor,
    ConstructRuleConstructionPlanFactory,
    ContainerConstructionPlanFactory,
)
from declarative_app.rules import RuleRegistry


@pytest.mark.asyncio_cooperative
async def test_construct(container):
    resolver = ConstructionResolver(
        factories=[
            ContainerConstructionPlanFactory(container),
            ConstructRuleConstructionPlanFactory(RuleRegistry(rules)),
        ]
    )
    container.add(Param(5))
    plans = list(resolver.resolve(Result))
    constructor = Constructor()
    results = await asyncio.gather(
        *(constructor.construct(plan) for plan in plans)
    )
    for result in results:
        assert isinstance(result, Result)


@pytest.mark.asyncio_cooperative
async def test_concurrent_construct(container):
    resolver = ConstructionResolver(
        factories=[
            ContainerConstructionPlanFactory(container),
            ConstructRuleConstructionPlanFactory(RuleRegistry(rules)),
        ]
    )
    container.add(Param(5))
    plans = list(resolver.resolve(Result))
    constructor = Constructor()
    plan = plans[0]
    results = await asyncio.gather(
        *(constructor.construct(plan) for _ in range(4))
    )
    for result in results:
        assert isinstance(result, Result)
        assert result == results[0]
        assert result.value == 25
