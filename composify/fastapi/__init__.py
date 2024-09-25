"""Supports for FastAPI integration."""

from .app import create_app, default_rules
from .lifespan import Lifespan, LifespanHook
from .router import APIRouterCollection, router_rule

__all__ = (
    "create_app",
    "default_rules",
    "LifespanHook",
    "Lifespan",
    "router_rule",
    "APIRouterCollection",
)
