from fixture.example_complex_rules import (
    Param,
    Param1,
    Result,
    infer_param_1,
    rules,
)

from declarative_app.construction import (
    ConstructionResolver,
    ConstructRuleConstructionPlanFactory,
    ContainerConstructionPlanFactory,
)
from declarative_app.rules import RuleRegistry, as_rule


def test_create_plan(container):
    resolver = ConstructionResolver(
        factories=[
            ContainerConstructionPlanFactory(container),
            ConstructRuleConstructionPlanFactory(RuleRegistry(rules)),
        ]
    )
    container.add(Param(5))
    plans = list(resolver.resolve(Result))
    assert len(plans) == 4, plans


def test_chain_length(container):
    resolver = ConstructionResolver(
        factories=[
            ContainerConstructionPlanFactory(container),
            ConstructRuleConstructionPlanFactory(
                RuleRegistry([as_rule(infer_param_1)])
            ),
        ]
    )
    container.add(Param(5))
    plans = list(resolver.resolve(Param1))
    assert len(plans) == 1, plans
    assert plans[0].chain_length == 1, plans[0]


def test_rule_resolver():
    resolver = ConstructionResolver(
        factories=[ConstructRuleConstructionPlanFactory(RuleRegistry(rules))]
    )
    plans = list(resolver.resolve(Result))
    assert len(plans) == 1, plans
    assert plans[0].chain_length == 2, plans[0]


def test_container_resolver(container):
    resolver = ConstructionResolver(
        factories=[
            ContainerConstructionPlanFactory(container),
        ]
    )
    container.add(Param(5))
    plans = list(resolver.resolve(Param))
    assert len(plans) == 1, plans
    assert plans[0].chain_length == 0, plans[0]
