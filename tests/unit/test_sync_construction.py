from dataclasses import dataclass

import pytest

from composify.builder import Builder
from composify.errors import AsyncBlueprintError
from composify.rules import rule
from tests.utils import blueprint, static


@dataclass(frozen=True)
class Value:
    value: int


@rule
def double(param: Value) -> Value:
    return Value(param.value * 2)


@rule
def quintuple(param: Value) -> Value:
    return Value(param.value * 5)


@rule
def squared(param: Value) -> Value:
    return Value(param.value**2)


def test_construct():
    plan = blueprint(
        double,
        param=static(Value(5)),
    )
    builder = Builder()
    result = builder.from_blueprint(plan)
    assert result == Value(10)


@rule
async def async_value() -> Value:
    return Value(1)


def test_construct_async():
    builder = Builder()

    plan = blueprint(
        async_value,
    )
    with pytest.raises(AsyncBlueprintError):
        builder.from_blueprint(plan)

    plan = blueprint(double, param=blueprint(async_value))
    with pytest.raises(AsyncBlueprintError):
        builder.from_blueprint(plan)


class ExecutionCounter:
    def __init__(self) -> None:
        self.execution = 0

    def __call__(self, f):
        def wrapper(*args, **kwargs):
            self.execution += 1
            return f(*args, **kwargs)

        return wrapper


def test_cached_construct():
    counter = ExecutionCounter()

    double_ = counter(double)
    quintuple_ = counter(quintuple)
    squared_ = counter(squared)

    testcases = {
        blueprint(
            double_,
            param=static(Value(5)),
        ): 10,
        blueprint(
            double_,
            param=static(Value(5)),
        ): 10,
        blueprint(
            quintuple_,
            param=blueprint(
                double_,
                param=static(Value(5)),
            ),
        ): 50,
        blueprint(
            double_,
            param=blueprint(
                quintuple_,
                param=static(Value(5)),
            ),
        ): 50,
        blueprint(
            squared_,
            param=blueprint(
                double_,
                param=static(Value(5)),
            ),
        ): 100,
    }
    assert len(testcases) == 4

    builder = Builder()

    plans, expected_results = zip(*testcases.items())

    results = tuple(builder.from_blueprint(plan) for plan in plans)
    for result, expected_result in zip(results, expected_results):
        assert isinstance(result, Value)
        assert result.value == expected_result

    assert counter.execution == 5
