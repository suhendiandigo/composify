from dataclasses import dataclass

import pytest

from composify.applications import ComposifyGetOrCreate
from composify.builder import Builder
from composify.errors import NonOptionalBuilderMismatchError
from composify.resolutions import UNIQUE
from composify.rules import rule
from tests.utils import ExecutionCounter, create_rule_resolver


@dataclass(frozen=True)
class Param:
    value: str


@dataclass(frozen=True)
class Result:
    value: str


@rule
def example_param() -> Param:
    return Param(5)


@rule
def example_param_0() -> Param:
    return Param(0)


@rule
def example_param_1() -> Param:
    return Param(-5)


@rule
def example_optional_rule(param: Param) -> Result | None:
    if param.value <= 0:
        return None
    return Result(param.value)


@rule
def example_failed_rule(param: Param) -> Result:
    return None


@rule
def example_not_optional_rule(param: Param) -> Result:
    return Result(param.value * 2)


def test_not_none():
    resolver = create_rule_resolver(example_param, example_optional_rule)

    blueprints = list(resolver.resolve(Result))
    assert len(blueprints) == 1

    builder = Builder()

    result = builder.from_blueprint(blueprints[0])
    assert result.value == 5


def test_optional():
    resolver = create_rule_resolver(example_param_0, example_optional_rule)

    blueprints = list(resolver.resolve(Result))
    assert len(blueprints) == 1

    builder = Builder()

    result = builder.from_blueprint(blueprints[0])
    assert result is None


def test_not_optional():
    resolver = create_rule_resolver(example_param_0, example_failed_rule)

    blueprints = list(resolver.resolve(Result))
    assert len(blueprints) == 1

    builder = Builder()

    with pytest.raises(NonOptionalBuilderMismatchError):
        builder.from_blueprint(blueprints[0])


def test_multiple_rule():
    counter = ExecutionCounter()

    resolver = create_rule_resolver(
        example_param_1,
        rule(counter(example_optional_rule)),
        example_not_optional_rule,
    )
    builder = Builder()

    get_or_create = ComposifyGetOrCreate(resolver, builder, UNIQUE)

    result = get_or_create.one(Result)
    assert result.value == -10
    assert counter.execution == 1
