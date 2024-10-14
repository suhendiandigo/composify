from dataclasses import dataclass
from typing import Generic, TypeVar

from composify.resolutions import EXHAUSTIVE, UNIQUE
from composify.rules import collect_rules, rule
from tests.utils import blueprint, create_rule_resolver

T = TypeVar("T")
U = TypeVar("U")
T_co = TypeVar("T_co", covariant=True)
T_covar = TypeVar("T_covar", contravariant=True)


@dataclass(frozen=True)
class Value(Generic[T]):
    value: T


@rule
async def int_value() -> Value[int]:
    return Value(5)


@rule
async def float_value() -> Value[float]:
    return Value(10.0)


@rule
async def str_value() -> Value[str]:
    return Value("123")


@dataclass(frozen=True)
class Pair(Generic[T, U]):
    value1: T
    value2: U


@rule
async def int_str_pair() -> Pair[int, str]:
    return Pair(5, "123")


@rule
async def str_int_pair() -> Pair[str, int]:
    return Pair("123", 5)


@rule
async def str_float_pair() -> Pair[str, float]:
    return Pair("123", 10.0)


@rule
async def str_float_pair_2() -> Pair[str, float]:
    return Pair("321", 10.0)


rules = collect_rules()


def test_generic_1(compare_blueprints):
    resolver = create_rule_resolver(*rules, default_resolution=UNIQUE)

    compare_blueprints(
        resolver.resolve(Value[str]),
        [
            blueprint(str_value),
        ],
    )

    compare_blueprints(
        resolver.resolve(Value[int]),
        [
            blueprint(int_value),
        ],
    )

    compare_blueprints(
        resolver.resolve(Value[float]),
        [
            blueprint(float_value),
        ],
    )


def test_generic_2(compare_blueprints):
    resolver = create_rule_resolver(*rules, default_resolution=EXHAUSTIVE)

    compare_blueprints(
        resolver.resolve(Pair[str, int]),
        [
            blueprint(str_int_pair),
        ],
    )

    compare_blueprints(
        resolver.resolve(Pair[str, float]),
        [blueprint(str_float_pair), blueprint(str_float_pair_2)],
    )

    compare_blueprints(
        resolver.resolve(Pair[int, str]),
        [
            blueprint(int_str_pair),
        ],
    )
