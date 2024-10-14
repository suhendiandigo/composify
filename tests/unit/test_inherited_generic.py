from dataclasses import dataclass
from typing import Generic, TypeVar

import pytest

from composify.errors import NoConstructorError, ResolutionFailureError
from composify.resolutions import EXHAUSTIVE
from composify.rules import collect_rules, rule
from tests.utils import blueprint, create_rule_resolver

T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True)
class Value(Generic[T]):
    value: T


T_co = TypeVar("T_co", covariant=True, bound=Value)
T_contra = TypeVar("T_contra", contravariant=True, bound=Value)


@dataclass(frozen=True)
class StrValue(Value[str]):
    pass


@dataclass(frozen=True)
class IntValue(Value[int]):
    pass


@dataclass(frozen=True)
class Container(Generic[T]):
    value: T


@dataclass(frozen=True)
class ChildContainer(Container[T]):
    pass


@rule
def get_int_container() -> Container[IntValue]:
    return Container(IntValue(10))


@rule
def get_str_container() -> Container[StrValue]:
    return Container(StrValue("100"))


@rule
def get_int_child_container() -> ChildContainer[IntValue]:
    return ChildContainer(IntValue(10))


@rule
def get_str_child_container() -> ChildContainer[StrValue]:
    return ChildContainer(StrValue("100"))


rules = collect_rules()


def test_invariant(compare_blueprints):
    resolver = create_rule_resolver(*rules, default_resolution=EXHAUSTIVE)

    with pytest.raises(ResolutionFailureError) as exc:
        (resolver.resolve(Container[Value[str]]),)
    assert exc.value.contains(NoConstructorError)

    compare_blueprints(
        resolver.resolve(Container[StrValue]),
        [
            blueprint(get_str_container),
        ],
    )

    compare_blueprints(
        resolver.resolve(Container[IntValue]),
        [
            blueprint(get_int_container),
        ],
    )

    compare_blueprints(
        resolver.resolve(ChildContainer[IntValue]),
        [
            blueprint(get_int_child_container),
        ],
    )

    compare_blueprints(
        resolver.resolve(ChildContainer[StrValue]),
        [
            blueprint(get_str_child_container),
        ],
    )


def test_covariant(compare_blueprints):
    resolver = create_rule_resolver(*rules, default_resolution=EXHAUSTIVE)

    compare_blueprints(
        resolver.resolve(Container[T_co]),
        [
            blueprint(get_str_container),
            blueprint(get_int_container),
        ],
    )


def test_contravariant(compare_blueprints):
    resolver = create_rule_resolver(*rules, default_resolution=EXHAUSTIVE)

    compare_blueprints(
        resolver.resolve(Container[T_contra]),
        [
            blueprint(get_str_container),
            blueprint(get_int_container),
        ],
    )
