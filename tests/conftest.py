from pytest import fixture

from declarative_app.container import Container


@fixture(scope="function")
def container() -> Container:
    return Container()
