from dataclasses import dataclass

from pytest import raises

from declarative_app.construction import (
    ConstructionResolver,
    ConstructRuleConstructionPlanFactory,
)
from declarative_app.errors import CyclicDependencyError, FailedToResolveError
from declarative_app.rules import RuleRegistry, collect_rules, rule


@dataclass(frozen=True)
class A:
    value: int


@dataclass(frozen=True)
class B:
    value: int


@rule(return_rule=True)
def create_a(param: A) -> B:
    return B(param.value * 2)


@rule(return_rule=True)
def create_b(param: B) -> A:
    return A(param.value * 2)


rules = collect_rules()


@rule(return_rule=True)
def default_a() -> A:
    return A(5)


rules_2 = collect_rules()


def test_raises_cyclic_dependency():
    resolver = ConstructionResolver(
        factories=[
            ConstructRuleConstructionPlanFactory(RuleRegistry(rules)),
        ]
    )
    with raises(FailedToResolveError) as exc:
        list(resolver.resolve(B))
    assert isinstance(exc.value.errors[0], CyclicDependencyError)


def test_cyclic_dependency_but_okay():
    resolver = ConstructionResolver(
        factories=[
            ConstructRuleConstructionPlanFactory(RuleRegistry(rules_2)),
        ]
    )
    plans = list(resolver.resolve(B))
    assert len(plans) > 0
