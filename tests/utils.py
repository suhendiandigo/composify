from declarative_app.construction import (
    ConstructionPlanFactory,
    ConstructionResolver,
    ConstructRuleConstructionPlanFactory,
)
from declarative_app.rules import ConstructRule, RuleRegistry, as_rule


def create_resolver(*factories: ConstructionPlanFactory):
    return ConstructionResolver(factories=factories)


def create_rule_plan_factory(*rules: ConstructRule):
    return ConstructRuleConstructionPlanFactory(
        RuleRegistry(as_rule(rule) for rule in rules)
    )


def create_rule_resolver(*rules: ConstructRule):
    return create_resolver(create_rule_plan_factory(*rules))
