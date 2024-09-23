from dataclasses import dataclass
from typing import Annotated

import pytest

from declarative_app.builder import Builder
from declarative_app.metadata import Name
from declarative_app.rules import collect_rules, rule
from tests.utils import create_rule_resolver


@dataclass(frozen=True)
class A:
    value: int


@rule
def create_a() -> A:
    return A(100)


rules_1 = collect_rules()


@rule
def create_special() -> Annotated[A, Name("special")]:
    return A(10)


rules_2 = collect_rules()


@pytest.mark.asyncio_cooperative
async def test_get_any():
    resolver = create_rule_resolver(*rules_1)
    plans = list(resolver.resolve(Annotated[A, Name("special")]))
    builder = Builder()
    assert len(plans) == 1
    plan = plans[0]
    result = await builder.from_blueprint(plan)
    assert isinstance(result, A)
    assert result.value == 100


@pytest.mark.asyncio_cooperative
async def test_get_special():
    resolver = create_rule_resolver(*rules_2)
    plans = list(resolver.resolve(Annotated[A, Name("special")]))
    builder = Builder()
    assert len(plans) == 1
    result = await builder.from_blueprint(plans[0])
    assert isinstance(result, A)
    assert result.value == 10

    plans = list(resolver.resolve(A))
    builder = Builder()
    assert len(plans) == 2
    result = await builder.from_blueprint(plans[0])
    assert result.value == 100
