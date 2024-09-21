import asyncio

import pytest
from fixture.example_complex_rules import Param, Result, rules

from declarative_app.construction import (
    ConstructionResolver,
    ConstructRuleConstructionPlanFactory,
    ContainerConstructionPlanFactory,
    construct,
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
    container.add(Param("123"))
    plans = list(resolver.resolve(Result))
    results = await asyncio.gather(*(construct(plan) for plan in plans))
    for result in results:
        assert isinstance(result, Result)
