from dataclasses import dataclass

import pytest

from composify.rules import as_rule, collect_rules, rule


@dataclass(frozen=True)
class Param:
    value: str


@dataclass(frozen=True)
class Result:
    value: str


@rule
async def example_async_rule(param: Param) -> Result:
    return Result(param.value)


@rule
def example_sync_rule(param: Param) -> Result:
    return Result(param.value)


rules = collect_rules()


def test_collect_rules():
    assert len(rules) == 2


def test_rule_async_metadata():
    rule = as_rule(example_async_rule)
    assert rule.is_async
    assert rule.function == example_async_rule
    assert rule.output_type == Result
    assert list(rule.parameter_types)[0][1] == Param


def test_rule_sync_metadata():
    rule = as_rule(example_sync_rule)
    assert not rule.is_async
    assert rule.function == example_sync_rule
    assert rule.output_type == Result
    assert list(rule.parameter_types)[0][1] == Param


def test_rule_sync_invocation():
    val = "Test Value"
    assert example_sync_rule(Param(val)) == Result(val)


@pytest.mark.asyncio_cooperative
async def test_rule_async_invocation():
    val = "Test Value"
    assert await example_async_rule(Param(val)) == Result(val)


def test_class_rule():
    @rule
    class Rule:
        def __init__(self, param: Param) -> None:
            self.value = param.value

    assert as_rule(Rule) is not None
