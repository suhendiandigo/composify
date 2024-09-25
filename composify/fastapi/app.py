import itertools
from collections.abc import Iterable

from fastapi import APIRouter, FastAPI

from composify import (
    Composify,
    Get,
    GetOrCreate,
    Injector,
    collect_rules,
    rule,
)
from composify.fastapi.hooks import Lifespan, LifespanHook
from composify.fastapi.router import APIRouterCollection
from composify.provider import ConstructorProvider
from composify.resolutions import EXHAUSTIVE
from composify.rules import ConstructRule


@rule
def collect_api_routers(get_or_create: GetOrCreate) -> APIRouterCollection:
    # Create all routers instances from loaded rules.
    # This essentially bootstraps the application since these routers are our root nodes.
    return APIRouterCollection(get_or_create.all(APIRouter, EXHAUSTIVE))


@rule
def collect_lifespan_hooks(
    _: APIRouterCollection, get: Get, inject: Injector
) -> Lifespan:
    # We need APIRouterCollection to bootstrap the creation of all routers.
    # Otherwise, there would be no hooks to collect.

    # We are using Get.all instead of GetOrCreate.all to avoid
    # creating instances of LifespanHook that are not dependency
    # of any of our loaded routers.

    lifespan_hooks = [  # type: ignore[var-annotated]
        inject(hook.on_lifespan) for hook in get.all(LifespanHook)
    ]
    return Lifespan(lifespan_hooks)


default_rules = collect_rules()


def create_app(
    providers: Iterable[ConstructorProvider], rules: Iterable[ConstructRule]
) -> FastAPI:
    return Composify(
        providers=providers,
        rules=itertools.chain(default_rules, rules),
    ).get_or_create(FastAPI)
