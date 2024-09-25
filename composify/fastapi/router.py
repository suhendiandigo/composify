from functools import wraps

from fastapi import APIRouter

from composify import rule
from composify.qualifiers import SelectFirst


# We add a SelectFirst qualifier to prevent duplicate API Routers.
# This is necessary due to our call to get_or_create.all(APIRouter, EXHAUSTIVE)
# which will try to get and create all possible APIRouter using permutations
# of all configurations.
# With SelectFirst qualifier, we limit the execution for each rule to the
# first permutation only.
@wraps(rule)
def router_rule(*args, **kwargs):
    if "dependency_qualifiers" in kwargs:
        kwargs["dependency_qualifiers"] = (
            *kwargs["dependency_qualifiers"],
            SelectFirst,
        )
    else:
        kwargs["dependency_qualifiers"] = (SelectFirst,)
    return rule(*args, **kwargs)


class APIRouterCollection(tuple[APIRouter, ...]):
    pass
