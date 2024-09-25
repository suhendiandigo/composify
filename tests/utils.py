import asyncio
from typing import Any

from composify.attributes import Name
from composify.blueprint import Blueprint, BlueprintResolver
from composify.constructor import ConstructorFunction
from composify.container import InstanceWrapper
from composify.metadata.attributes import AttributeSet
from composify.provider import (
    ConstructorProvider,
    RuleBasedConstructorProvider,
    Static,
)
from composify.resolutions import EXHAUSTIVE
from composify.rules import ConstructRule, RuleRegistry, as_rule
from composify.types import resolve_type_name


def create_resolver(*factories: ConstructorProvider):
    return BlueprintResolver(providers=factories, default_resolution=EXHAUSTIVE)


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
    result = f"{indent_str}{name + ': ' if name else ''}{construction.output_type!s} <- {construction.source}"
    for parameter_name, parameter in construction.dependencies:
        result += "\n" + _format_construction_string(
            parameter_name, parameter, indent, level + 1
        )
    return result


def format_construction_string(construction: Blueprint, indent: int = 2) -> str:
    return _format_construction_string("", construction, indent, 0)


def blueprint(
    constructor: ConstructorFunction,
    **dependencies: Blueprint,
) -> Blueprint:
    return Blueprint(
        "__test_blueprint__",  # Not used for building
        constructor,
        is_async=any(
            (
                asyncio.iscoroutinefunction(constructor),
                *(dependency.is_async for dependency in dependencies.values()),
            )
        ),
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


def instance(
    type_: type,
    idx: int,
    attributes: AttributeSet = None,
    is_primary: bool = False,
    priority: int = 0,
) -> Blueprint:
    name = f"{resolve_type_name(type_)}_{idx}"
    return Blueprint(
        "__test_instance",  # Not used for building
        InstanceWrapper(
            instance=None,
            instance_type=type_,
            instance_name=name,
            attributes=attributes or AttributeSet((Name(name),)),
            is_primary=is_primary,
            priority=priority,
        ),
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
