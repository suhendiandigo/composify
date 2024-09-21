import pytest
from fixture.example_rules import (
    Param,
    Result,
    example_async_rule,
    example_sync_rule,
    rules,
)

from declarative_app.rules import get_rule_metadata


def test_collect_rules():
    assert len(rules) == 2


def test_rule_async_metadata():
    rule = get_rule_metadata(example_async_rule)
    assert rule.is_async
    assert rule.function == example_async_rule
    assert rule.output_type == Result
    assert rule.parameter_types["param"] == Param


def test_rule_sync_metadata():
    rule = get_rule_metadata(example_sync_rule)
    assert not rule.is_async
    assert rule.function == example_sync_rule
    assert rule.output_type == Result
    assert rule.parameter_types["param"] == Param


def test_rule_sync_invocation():
    val = "Test Value"
    assert example_sync_rule(Param(val)) == Result(val)


@pytest.mark.asyncio_cooperative
async def test_rule_async_invocation():
    val = "Test Value"
    assert await example_async_rule(Param(val)) == Result(val)
