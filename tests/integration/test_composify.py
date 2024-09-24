from dataclasses import dataclass

import pytest

from composify import Composify, rule
from composify.errors import AsyncBlueprintError, MultipleResolutionError


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

    assert composify.get(Value, resolution_mode="default") == create_value()

    composify.add_rule(create_value_2)

    with pytest.raises(MultipleResolutionError):
        composify.get(Value, resolution_mode="default")

    assert composify.get_all(Value) == (create_value(), create_value_2())


def test_first_resolution():
    composify = Composify()

    composify.add_rule(create_value)

    assert (
        composify.get(Value, resolution_mode="select_first") == create_value()
    )

    composify.add_rule(create_value_2)

    assert (
        composify.get(Value, resolution_mode="select_first") == create_value()
    )

    assert composify.get_all(Value) == (create_value(), create_value_2())


@rule
async def async_create_value() -> Value:
    return Value(5)


@rule
async def async_create_value_2() -> Value:
    return Value(10)


@pytest.mark.asyncio_cooperative
async def test_async_default_resolution():
    composify = Composify()

    composify.add_rule(async_create_value)

    assert (
        await composify.aget(Value, resolution_mode="default")
        == create_value()
    )

    composify.add_rule(async_create_value_2)

    with pytest.raises(MultipleResolutionError):
        await composify.aget(Value, resolution_mode="default")

    assert await composify.aget_all(Value) == (
        create_value(),
        create_value_2(),
    )


@pytest.mark.asyncio_cooperative
async def test_async_first_resolution():
    composify = Composify()

    composify.add_rule(async_create_value)

    assert (
        await composify.aget(Value, resolution_mode="select_first")
    ) == create_value()

    composify.add_rule(async_create_value_2)

    assert (
        await composify.aget(Value, resolution_mode="select_first")
    ) == create_value()

    assert (await composify.aget_all(Value)) == (
        create_value(),
        create_value_2(),
    )


def test_sync_build_on_async():
    composify = Composify()

    composify.add_rule(async_create_value)

    with pytest.raises(AsyncBlueprintError):
        composify.get(Value, resolution_mode="default")
