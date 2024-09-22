from fixture.example_complex_rules import (
    Param,
    Param1,
    Result,
    infer_param_1,
    rules,
)

from declarative_app.construction import ContainerConstructionPlanFactory
from tests.utils import (
    create_resolver,
    create_rule_plan_factory,
    create_rule_resolver,
)


def test_create_plan(container):
    resolver = create_resolver(
        ContainerConstructionPlanFactory(container),
        create_rule_plan_factory(*rules),
    )
    container.add(Param(5))
    plans = list(resolver.resolve(Result))
    assert len(plans) == 4, plans


def test_chain_length(container):
    resolver = create_resolver(
        ContainerConstructionPlanFactory(container),
        create_rule_plan_factory(infer_param_1),
    )
    container.add(Param(5))
    plans = list(resolver.resolve(Param1))
    assert len(plans) == 1, plans
    assert plans[0].chain_length == 1, plans[0]


def test_rule_resolver():
    resolver = create_rule_resolver(*rules)

    plans = list(resolver.resolve(Result))
    assert len(plans) == 1, plans
    assert plans[0].chain_length == 2, plans[0]


def test_container_resolver(container, container_resolver):
    container.add(Param(5))
    plans = list(container_resolver.resolve(Param))
    assert len(plans) == 1, plans
    assert plans[0].chain_length == 0, plans[0]
