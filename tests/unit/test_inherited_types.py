from dataclasses import dataclass
from typing import Annotated

import pytest

from composify.errors import NoConstructorError, ResolutionFailureError
from composify.metadata.qualifiers import DisallowSubclass
from composify.rules import rule
from tests.utils import blueprint, create_rule_resolver


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
async def test_subclasses(compare_blueprints):
    resolver = create_rule_resolver(create_c)

    compare_blueprints(
        resolver.resolve(A),
        [blueprint(create_c)],
    )

    with pytest.raises(ResolutionFailureError) as exc:
        resolver.resolve(B)
    assert exc.value.contains(NoConstructorError)

    compare_blueprints(
        resolver.resolve(C),
        [blueprint(create_c)],
    )


@pytest.mark.asyncio_cooperative
async def test_disallowed_subclasses(compare_blueprints):
    resolver = create_rule_resolver(create_c)

    with pytest.raises(ResolutionFailureError) as exc:
        resolver.resolve(Annotated[A, DisallowSubclass()])
    assert exc.value.contains(NoConstructorError)

    with pytest.raises(ResolutionFailureError) as exc:
        resolver.resolve(B)
    assert exc.value.contains(NoConstructorError)

    compare_blueprints(
        resolver.resolve(C),
        [blueprint(create_c)],
    )


@pytest.mark.asyncio_cooperative
async def test_allowed_subclasses(compare_blueprints):
    resolver = create_rule_resolver(create_c)

    compare_blueprints(
        resolver.resolve(Annotated[A, DisallowSubclass(False)]),
        [blueprint(create_c)],
    )

    with pytest.raises(ResolutionFailureError) as exc:
        resolver.resolve(B)
    assert exc.value.contains(NoConstructorError)

    compare_blueprints(
        resolver.resolve(C),
        [blueprint(create_c)],
    )
