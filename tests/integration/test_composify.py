from dataclasses import dataclass

import pytest

from composify import AsyncComposify, Composify, rule
from composify.errors import MultipleResolutionError
from composify.resolutions import EXHAUSTIVE, SELECT_FIRST
from composify.rules import AsyncRuleNotAllowedError


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
    composify = Composify()

    composify.add_rule(create_value)

    assert (
        composify.get_or_create.one(Value, resolution_mode=EXHAUSTIVE)
        == create_value()
    )

    composify.add_rule(create_value_2)

    with pytest.raises(MultipleResolutionError):
        composify.get_or_create.one(Value, resolution_mode=EXHAUSTIVE)

    assert composify.get_or_create.all(Value, resolution_mode=EXHAUSTIVE) == (
        create_value(),
        create_value_2(),
    )


def test_first_resolution():
    composify = Composify()

    composify.add_rule(create_value)

    assert (
        composify.get_or_create.one(Value, resolution_mode=SELECT_FIRST)
        == create_value()
    )

    composify.add_rule(create_value_2)

    assert (
        composify.get_or_create.one(Value, resolution_mode=SELECT_FIRST)
        == create_value()
    )

    assert composify.get_or_create.all(Value, resolution_mode=SELECT_FIRST) == (
        create_value(),
        create_value_2(),
    )


@rule
async def async_create_value() -> Value:
    return Value(5)


@rule
async def async_create_value_2() -> Value:
    return Value(10)


@pytest.mark.asyncio_cooperative
async def test_async_default_resolution():
    composify = AsyncComposify()

    composify.add_rule(async_create_value)

    assert (
        await composify.aget_or_create.one(Value, resolution_mode=EXHAUSTIVE)
        == create_value()
    )

    composify.add_rule(async_create_value_2)

    with pytest.raises(MultipleResolutionError):
        await composify.aget_or_create.one(Value, resolution_mode=EXHAUSTIVE)

    assert await composify.aget_or_create.all(
        Value, resolution_mode=EXHAUSTIVE
    ) == (
        create_value(),
        create_value_2(),
    )


@pytest.mark.asyncio_cooperative
async def test_async_first_resolution():
    composify = AsyncComposify()

    composify.add_rule(async_create_value)

    assert (
        await composify.aget_or_create.one(Value, resolution_mode=SELECT_FIRST)
    ) == create_value()

    composify.add_rule(async_create_value_2)

    assert (
        await composify.aget_or_create.one(Value, resolution_mode=SELECT_FIRST)
    ) == create_value()

    assert (
        await composify.aget_or_create.all(Value, resolution_mode=SELECT_FIRST)
    ) == (
        create_value(),
        create_value_2(),
    )


def test_sync_build_on_async():
    composify = Composify()

    with pytest.raises(AsyncRuleNotAllowedError):
        composify.add_rule(async_create_value)
