from dataclasses import dataclass
from typing import Annotated

import pytest

from composify.blueprint import FailedToResolveError
from composify.metadata.qualifiers import DisallowSubclass
from composify.rules import rule
from tests.utils import blueprint, compare_blueprints, create_rule_resolver


@dataclass(frozen=True)
class A:
    value: int


@dataclass(frozen=True)
class B:
    value: int


@dataclass(frozen=True)
class C(A):
    value: int


@rule
def create_a() -> A:
    return A(10)


@rule
def create_c() -> C:
    return C(100)


@pytest.mark.asyncio_cooperative
async def test_subclasses():
    resolver = create_rule_resolver(create_c)

    compare_blueprints(
        resolver.resolve(A),
        [blueprint(create_c)],
    )

    with pytest.raises(FailedToResolveError):
        resolver.resolve(B)

    compare_blueprints(
        resolver.resolve(C),
        [blueprint(create_c)],
    )


@pytest.mark.asyncio_cooperative
async def test_disallowed_subclasses():
    resolver = create_rule_resolver(create_c)

    with pytest.raises(FailedToResolveError):
        resolver.resolve(Annotated[A, DisallowSubclass()])

    with pytest.raises(FailedToResolveError):
        resolver.resolve(B)

    compare_blueprints(
        resolver.resolve(C),
        [blueprint(create_c)],
    )


@pytest.mark.asyncio_cooperative
async def test_allowed_subclasses():
    resolver = create_rule_resolver(create_c)

    compare_blueprints(
        resolver.resolve(Annotated[A, DisallowSubclass(False)]),
        [blueprint(create_c)],
    )

    with pytest.raises(FailedToResolveError):
        resolver.resolve(B)

    compare_blueprints(
        resolver.resolve(C),
        [blueprint(create_c)],
    )


# @pytest.mark.asyncio_cooperative
# async def test_covariant():
#     resolver = create_rule_resolver(create_c)

#     compare_blueprints(
#         resolver.resolve(Annotated[A, Variance("covariant")]),
#         [blueprint(create_c)],
#     )

#     with pytest.raises(FailedToResolveError):
#         resolver.resolve(Annotated[B, Variance("covariant")])

#     compare_blueprints(
#         resolver.resolve(Annotated[C, Variance("covariant")]),
#         [blueprint(create_c)],
#     )


# @pytest.mark.asyncio_cooperative
# async def test_contravariant():
#     resolver = create_rule_resolver(create_a)

#     compare_blueprints(
#         resolver.resolve(Annotated[A, Variance("contravariant")]),
#         [blueprint(create_a)],
#     )

#     with pytest.raises(FailedToResolveError):
#         list(resolver.resolve(Annotated[B, Variance("contravariant")]))

#     compare_blueprints(
#         resolver.resolve(Annotated[C, Variance("contravariant")]),
#         [blueprint(create_a)],
#     )


# @pytest.mark.asyncio_cooperative
# async def test_invariant():
#     resolver = create_rule_resolver(create_c)

#     with pytest.raises(FailedToResolveError):
#         list(resolver.resolve(Annotated[A, Variance("invariant")]))

#     with pytest.raises(FailedToResolveError):
#         list(resolver.resolve(Annotated[B, Variance("invariant")]))

#     compare_blueprints(
#         resolver.resolve(Annotated[C, Variance("invariant")]),
#         [blueprint(create_c)],
#     )
