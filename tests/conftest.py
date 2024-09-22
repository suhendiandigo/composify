from pytest import fixture

from declarative_app.construction import (
    ConstructionResolver,
    ContainerConstructionPlanFactory,
)
from declarative_app.container import Container


@fixture(scope="function")
def container() -> Container:
    return Container()


@fixture(scope="function")
def container_resolver(container) -> ConstructionResolver:
    return ConstructionResolver([ContainerConstructionPlanFactory(container)])
