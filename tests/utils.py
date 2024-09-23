import asyncio
from typing import Any

from declarative_app.blueprint import Blueprint, BlueprintResolver
from declarative_app.constructor import ConstructorFunction
from declarative_app.provider import (
    ConstructorProvider,
    RuleBasedConstructorProvider,
    Static,
)
from declarative_app.rules import ConstructRule, RuleRegistry, as_rule


def create_resolver(*factories: ConstructorProvider):
    return BlueprintResolver(factories=factories)


def create_rule_provider(*rules: ConstructRule):
    return RuleBasedConstructorProvider(
        RuleRegistry(as_rule(rule) for rule in rules)
    )


def create_rule_resolver(*rules: ConstructRule):
    return create_resolver(create_rule_provider(*rules))


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


def blueprint(
    constructor: ConstructorFunction,
    **dependencies: Blueprint,
) -> Blueprint:
    return Blueprint(
        "__test_blueprint__",  # Not used for building
        constructor,
        is_async=asyncio.iscoroutinefunction(constructor),
        output_type=type,  # Not used for building
        dependencies=tuple(dependencies.items()),
        chain_length=0,  # Not used for building
    )


def static(
    value: Any,
) -> Blueprint:
    return Blueprint(
        "__test_static__",  # Not used for building
        Static(value),
        is_async=False,
        output_type=type,  # Not used for building
        dependencies=tuple(),
        chain_length=0,  # Not used for building
    )
