from fixture.example_complex_rules import (
    Param,
    Result,
    example_sync_rule,
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
    container.add(Param("123"))
    plans = list(resolver.resolve(Result))
    assert len(plans) == 2


def test_chain_length(container):
    resolver = ConstructionResolver(
        factories=[
            ContainerConstructionPlanFactory(container),
            ConstructRuleConstructionPlanFactory(
                RuleRegistry([as_rule(example_sync_rule)])
            ),
        ]
    )
    container.add(Param("123"))
    plans = list(resolver.resolve(Result))
    assert len(plans) == 1
    assert plans[0].chain_length == 1


def test_rule_resolver():
    resolver = ConstructionResolver(
        factories=[ConstructRuleConstructionPlanFactory(RuleRegistry(rules))]
    )
    plans = list(resolver.resolve(Result))
    assert len(plans) == 1
    assert plans[0].chain_length == 1


def test_container_resolver(container):
    resolver = ConstructionResolver(
        factories=[
            ContainerConstructionPlanFactory(container),
        ]
    )
    container.add(Param("123"))
    plans = list(resolver.resolve(Param))
    assert len(plans) == 1
    assert plans[0].chain_length == 0
