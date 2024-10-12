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
from composify.resolutions import UNIQUE
from composify.rules import ConstructRule, as_rule


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


@rule
def __create_default_composify_fastapi(
    routers: APIRouterCollection, lifespan: Lifespan
) -> FastAPI:
    fast_api = FastAPI(
        title="Composify FastAPI",
        lifespan=lifespan,  # We use the lifespan injected by Composify.
    )

    for router in routers:
        fast_api.include_router(router)

    return fast_api


def _has_fastapi_rule(all_rules: Iterable[ConstructRule]) -> bool:
    for r in all_rules:
        if issubclass(r.output_type, FastAPI):
            return True

    return False


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
    all_rules = tuple(itertools.chain(default_rules, rules))

    if not _has_fastapi_rule(all_rules):
        all_rules = all_rules + (as_rule(__create_default_composify_fastapi),)

    return Composify(
        providers=providers,
        rules=all_rules,
        default_resolution=UNIQUE,
    ).get_or_create.one(FastAPI)
