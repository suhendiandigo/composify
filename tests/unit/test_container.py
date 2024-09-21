from typing import Annotated

from fixture.example_rules import Param, Result
from pytest import fixture, raises

from declarative_app.container import Container
from declarative_app.errors import (
    AmbiguousInstanceError,
    ConflictingInstanceNameError,
    InstanceNotFoundError,
    MultiplePrimaryInstanceError,
)
from declarative_app.metadata import Name


@fixture(scope="function")
def container() -> Container:
    return Container()


def test_add(container: Container):
    container.add(Param("123"))
    container.add(Result("323"))

    assert container.get(Param).value == "123"
    assert container.get(Result).value == "323"


def test_get_primary(container: Container):
    container.add(Param("123"))
    container.add(Param("323"), is_primary=True)

    assert container.get(Param).value == "323"


def test_get_using_qualifier(container: Container):
    container.add(Param("123"), name="test1")
    container.add(Param("323"), name="test2")

    assert container.get(Annotated[Param, Name("test1")]).value == "123"
    assert container.get(Annotated[Param, Name("test2")]).value == "323"


def test_remove(container: Container):
    a = Param("123")
    container.add(a)

    assert container.get(Param) == a

    container.remove(a)

    with raises(InstanceNotFoundError):
        container.get(Param)


def test_acecss_by_name(container: Container):
    name = "test1"
    a = Param("123")
    container.add(a, name=name)
    container.add(Param("323"))

    assert container.get_by_name(name) == a

    container.remove(a)

    with raises(InstanceNotFoundError):
        container.get_by_name(name)


def test_get_error(container: Container):
    with raises(InstanceNotFoundError):
        container.get(Param)


def test_ambiguous_error(container: Container):
    container.add(Param("123"))
    container.add(Param("323"))

    with raises(AmbiguousInstanceError):
        container.get(Param)


def test_conflicting_error(container: Container):
    container.add(Param("123"), name="test1")

    with raises(ConflictingInstanceNameError):
        container.add(Param("323"), name="test1")


def test_multiple_primary_error(container: Container):
    container.add(Param("123"), is_primary=True)

    with raises(MultiplePrimaryInstanceError):
        container.add(Param("323"), is_primary=True)
