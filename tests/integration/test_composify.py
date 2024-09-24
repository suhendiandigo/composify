from dataclasses import dataclass

import pytest

from composify import Composify, rule
from composify.errors import MultipleResolutionError


@dataclass
class Value:
    value: int


@rule
def create_value() -> Value:
    return Value(5)


@rule
def create_value_2() -> Value:
    return Value(10)


def test_default_resolution():
    composify = Composify(resolution_mode="default")

    composify.add_rule(create_value)

    assert composify.build(Value) == create_value()

    composify.add_rule(create_value_2)

    with pytest.raises(MultipleResolutionError):
        composify.build(Value)


def test_first_resolution():
    composify = Composify(resolution_mode="select_first")

    composify.add_rule(create_value)

    assert composify.build(Value) == create_value()

    composify.add_rule(create_value_2)

    assert composify.build(Value) == create_value()
