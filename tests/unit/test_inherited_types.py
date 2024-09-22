from dataclasses import dataclass
from typing import Annotated

import pytest

from declarative_app.construction import (
    ConstructionResolver,
    Constructor,
    ConstructRuleConstructionPlanFactory,
)
from declarative_app.errors import FailedToResolveError
from declarative_app.metadata.qualifiers import Variance
from declarative_app.rules import RuleRegistry, as_rule, rule


@dataclass(frozen=True)
class A:
    value: int


@dataclass(frozen=True)
class B(A):
    value: int


@rule
def create_a() -> A:
    return A(10)


@rule
def create_b() -> B:
    return B(100)


@pytest.mark.asyncio_cooperative
async def test_covariant():
    resolver = ConstructionResolver(
        factories=[
            ConstructRuleConstructionPlanFactory(
                RuleRegistry([as_rule(create_b)])
            ),
        ]
    )
    plans = list(resolver.resolve(Annotated[A, Variance("covariant")]))
    assert len(plans) == 1
    constructor = Constructor()
    result = await constructor.construct(plans[0])
    assert isinstance(result, B)


@pytest.mark.asyncio_cooperative
async def test_contravariant():
    resolver = ConstructionResolver(
        factories=[
            ConstructRuleConstructionPlanFactory(
                RuleRegistry([as_rule(create_a)])
            ),
        ]
    )
    plans = list(resolver.resolve(Annotated[B, Variance("contravariant")]))
    assert len(plans) == 1
    constructor = Constructor()
    result = await constructor.construct(plans[0])
    assert isinstance(result, A)


@pytest.mark.asyncio_cooperative
async def test_invariant():
    resolver = ConstructionResolver(
        factories=[
            ConstructRuleConstructionPlanFactory(
                RuleRegistry([as_rule(create_b)])
            ),
        ]
    )
    with pytest.raises(FailedToResolveError):
        list(resolver.resolve(Annotated[A, Variance("invariant")]))
