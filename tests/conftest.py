from pytest import fixture

from declarative_app.blueprint import BlueprintResolver
from declarative_app.container import Container
from declarative_app.provider import ContainerInstanceProvider


@fixture(scope="function")
def container() -> Container:
    return Container()


@fixture(scope="function")
def container_resolver(container) -> BlueprintResolver:
    return BlueprintResolver([ContainerInstanceProvider(container)])
