"""Support for FastAPI creation.


Example:
    from composify import collect_rules, rule
    from composify.fastapi import APIRouterCollection, create_app, Lifespan
    from fastapi import FastAPI

    @rule
    def create_fastapi(routers: APIRouterCollection, lifespan: Lifespan) -> FastAPI:
        # Standard FastAPI bootstrap
        fast_api = FastAPI(
            title="Example",
            lifespan=lifespan,
        )

        # APIRouterCollection contains all APIRouters declared
        # using the @router_rule decorator.
        for router in routers:
            fast_api.include_router(router)

        return fast_api

    rules = collect_rules()

    app = create_app(
        rules=rules
    )

"""

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
from composify.fastapi.lifespan import Lifespan, LifespanHook
from composify.provider import ConstructorProvider
from composify.resolutions import SELECT_FIRST, UNIQUE
from composify.rules import ConstructRule


class APIRouterCollection(tuple[APIRouter, ...]):
    """A collect of declared API routers."""

    pass


@rule
def collect_api_routers(get_or_create: GetOrCreate) -> APIRouterCollection:
    """Create all routers instances from loaded rules.

    This essentially bootstraps the application since these routers are our root nodes.
    """
    return APIRouterCollection(get_or_create.all(APIRouter, UNIQUE))


@rule
def collect_lifespan_hooks(
    _: APIRouterCollection, get: Get, inject: Injector
) -> Lifespan:
    """We need APIRouterCollection to bootstrap the creation of all routers.
    Otherwise, there would be no hooks to collect.
    We are using Get.all instead of GetOrCreate.all to avoid
    creating instances of LifespanHook that are not dependencies
    of any of our loaded routers.
    """
    lifespan_hooks = [  # type: ignore[var-annotated]
        inject(hook.on_lifespan) for hook in get.all(LifespanHook)
    ]
    return Lifespan(lifespan_hooks)


default_rules = collect_rules()


def create_app(
    rules: Iterable[ConstructRule],
    providers: Iterable[ConstructorProvider] = (),
) -> FastAPI:
    """Create a FastAPI object using providers and rules.

    Args:
        rules (Iterable[ConstructRule]): Rules to use.
        providers (Iterable[ConstructorProvider]): Providers to use.

    Returns:
        FastAPI: A FastAPI instance.


    """
    return Composify(
        providers=providers,
        rules=itertools.chain(default_rules, rules),
        default_resolution=SELECT_FIRST,
    ).get_or_create.one(FastAPI)
