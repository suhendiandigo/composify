"""Add support for fastapi.APIRouter retrieval."""

from collections.abc import Callable, Iterable

from fastapi import APIRouter

from composify import rule
from composify.metadata.qualifiers import BaseQualifierMetadata
from composify.qualifiers import SelectFirst


def router_rule(
    f: Callable[..., APIRouter] | None = None,
    /,
    *,
    priority: int = 0,
    dependency_qualifiers: Iterable[BaseQualifierMetadata] | None = None,
):
    """Marks a function as APIRouter rule. Allowing collection via collect_rules().

    This decorator acts exactly the same as @rule except for an additional
    SelectFirst qualifier.

    A SelectFirst qualifier is necessary to prevent duplicate API Routers.
    This is necessary due to our call to get_or_create.all(APIRouter, EXHAUSTIVE)
    which will try to get and create all possible APIRouter using permutations
    of all configurations.
    With a SelectFirst qualifier, we limit the execution for each rule to the
    first permutation only.

    Args:
        f (RuleFunctionType | None, optional): The function or class to mark as a rule. Defaults to None.
        priority (int, optional): The resolution priority. Higher value equals higher priority. Defaults to 0.
        dependency_qualifiers (Iterable[BaseQualifierMetadata] | None, optional): Add qualifiers to all dependencies. Defaults to None.

    Returns:
        The input function returning APIRouter object.
    """
    if dependency_qualifiers:
        dependency_qualifiers = (
            *dependency_qualifiers,
            SelectFirst,
        )
    else:
        dependency_qualifiers = (SelectFirst,)
    return rule(
        f, priority=priority, dependency_qualifiers=dependency_qualifiers
    )


class APIRouterCollection(tuple[APIRouter, ...]):
    """A collect of declared API routers."""

    pass
