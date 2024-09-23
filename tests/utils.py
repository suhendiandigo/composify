from declarative_app.blueprint import Blueprint, BlueprintResolver
from declarative_app.provider import (
    ConstructorProvider,
    RuleBasedConstructorProvider,
)
from declarative_app.rules import ConstructRule, RuleRegistry, as_rule


def create_resolver(*factories: ConstructorProvider):
    return BlueprintResolver(factories=factories)


def create_rule_plan_factory(*rules: ConstructRule):
    return RuleBasedConstructorProvider(
        RuleRegistry(as_rule(rule) for rule in rules)
    )


def create_rule_resolver(*rules: ConstructRule):
    return create_resolver(create_rule_plan_factory(*rules))


def _format_construction_string(
    name: str, construction: Blueprint, indent: int, level: int
) -> str:
    indent_str = " " * (level * indent)
    result = f"{indent_str}{name + ": " if name else ''}{construction.output_type!s} <- {construction.source}"
    for parameter_name, parameter in construction.dependencies:
        result += "\n" + _format_construction_string(
            parameter_name, parameter, indent, level + 1
        )
    return result


def format_construction_string(
    construction: Blueprint, indent: int = 2
) -> str:
    return _format_construction_string("", construction, indent, 0)
