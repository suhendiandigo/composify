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
        dependencies=frozenset(dependencies.items()),
        priority=tuple(),  # Not used for building
    )


def static(
    value: Any,
) -> Blueprint:
    return Blueprint(
        "__test_static__",  # Not used for building
        Static(value),
        is_async=False,
        output_type=type,  # Not used for building
        dependencies=frozenset(),
        priority=tuple(),  # Not used for building
    )


def _find_difference(
    result: Blueprint, expected: Blueprint, path: tuple
) -> tuple | None:
    if (
        result.constructor != expected.constructor
        or result.is_async != expected.is_async
    ):
        return path
    r_depends = tuple(sorted(result.dependencies))
    e_depends = tuple(sorted(expected.dependencies))
    if len(r_depends) != len(e_depends):
        return path
    for (r_name, r_depend), (e_name, e_depend) in zip(r_depends, e_depends):
        if r_name != e_name:
            return path
        return _find_difference(r_depend, e_depend, path + (r_name,))


def find_difference(result: Blueprint, expected: Blueprint) -> tuple | None:
    return _find_difference(result, expected, tuple())
