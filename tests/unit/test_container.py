from dataclasses import dataclass
from typing import Annotated

from pytest import raises

from composify.container import Container
from composify.errors import (
    AmbiguousInstanceError,
    ConflictingInstanceNameError,
    InstanceNotFoundError,
    MultiplePrimaryInstanceError,
)
from composify.metadata import Name


@dataclass(frozen=True)
class A:
    value: str


@dataclass(frozen=True)
class B:
    value: str


@dataclass(frozen=True)
class C(A):
    pass


def test_add(container: Container):
    container.add(A("123"))
    container.add(B("323"))

    assert container.get(A).value == "123"
    assert container.get(B).value == "323"


def test_get_primary(container: Container):
    container.add(A("123"))
    container.add(A("323"), is_primary=True)

    assert container.get(A).value == "323"


def test_get_using_qualifier(container: Container):
    container.add(A("123"), name="test1")
    container.add(A("323"), name="test2")

    assert container.get(Annotated[A, Name("test1")]).value == "123"
    assert container.get(Annotated[A, Name("test2")]).value == "323"


def test_remove(container: Container):
    a = A("123")
    container.add(a)

    assert container.get(A) == a

    container.remove(a)

    with raises(InstanceNotFoundError):
        container.get(A)


def test_access_by_name(container: Container):
    name = "test1"
    a = A("123")
    container.add(a, name=name)
    container.add(A("323"))

    assert container.get_by_name(name) == a

    container.remove(a)

    with raises(InstanceNotFoundError):
        container.get_by_name(name)


def test_get_error(container: Container):
    with raises(InstanceNotFoundError):
        container.get(A)


def test_ambiguous_error(container: Container):
    container.add(A("123"))
    container.add(A("323"))

    with raises(AmbiguousInstanceError):
        container.get(A)


def test_conflicting_error(container: Container):
    container.add(A("123"), name="test1")

    with raises(ConflictingInstanceNameError):
        container.add(A("323"), name="test1")


def test_multiple_primary_error(container: Container):
    container.add(A("123"), is_primary=True)

    with raises(MultiplePrimaryInstanceError):
        container.add(A("323"), is_primary=True)


# def test_invariant(container: Container):
#     a = A("123")
#     c = C("321")
#     container.add(a)
#     container.add(c)

#     assert a == container.get(Annotated[A, Invariant])
#     assert c == container.get(Annotated[C, Invariant])
#     with raises(InstanceNotFoundError):
#         container.get(B)


# def test_covariant(container: Container):
#     c = C("123")
#     container.add(c)

#     assert c == container.get(Annotated[A, Covariant])
#     assert c == container.get(Annotated[C, Covariant])
#     with raises(InstanceNotFoundError):
#         container.get(B)


# def test_contravariant(container: Container):
#     a = A("123")
#     container.add(a)

#     assert a == container.get(Annotated[A, Contravariant])
#     assert a == container.get(Annotated[C, Contravariant])
#     with raises(InstanceNotFoundError):
#         container.get(B)
