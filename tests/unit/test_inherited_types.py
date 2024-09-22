from dataclasses import dataclass
from typing import Annotated

import pytest

from declarative_app.construction import Constructor
from declarative_app.errors import FailedToResolveError
from declarative_app.metadata.qualifiers import Variance
from declarative_app.rules import rule
from tests.utils import create_rule_resolver


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
async def test_covariant():
    resolver = create_rule_resolver(create_c)
    constructor = Constructor()

    plans = list(resolver.resolve(Annotated[A, Variance("covariant")]))
    assert len(plans) == 1
    result = await constructor.construct(plans[0])
    assert isinstance(result, C)

    plans = list(resolver.resolve(Annotated[C, Variance("covariant")]))
    assert len(plans) == 1
    result = await constructor.construct(plans[0])
    assert isinstance(result, C)

    with pytest.raises(FailedToResolveError):
        list(resolver.resolve(Annotated[B, Variance("covariant")]))


@pytest.mark.asyncio_cooperative
async def test_contravariant():
    resolver = create_rule_resolver(create_a)
    constructor = Constructor()

    plans = list(resolver.resolve(Annotated[C, Variance("contravariant")]))
    assert len(plans) == 1
    result = await constructor.construct(plans[0])
    assert isinstance(result, A)

    plans = list(resolver.resolve(Annotated[A, Variance("contravariant")]))
    assert len(plans) == 1
    result = await constructor.construct(plans[0])
    assert isinstance(result, A)

    with pytest.raises(FailedToResolveError):
        list(resolver.resolve(Annotated[B, Variance("contravariant")]))


@pytest.mark.asyncio_cooperative
async def test_invariant():
    resolver = create_rule_resolver(create_c)
    constructor = Constructor()

    plans = list(resolver.resolve(Annotated[C, Variance("invariant")]))
    assert len(plans) == 1
    result = await constructor.construct(plans[0])
    assert isinstance(result, C)

    with pytest.raises(FailedToResolveError):
        list(resolver.resolve(Annotated[A, Variance("invariant")]))

    with pytest.raises(FailedToResolveError):
        list(resolver.resolve(Annotated[B, Variance("invariant")]))
