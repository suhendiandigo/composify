"""Supports for FastAPI integration."""

from .app import APIRouterCollection, create_app, default_rules
from .lifespan import Lifespan, LifespanHook

__all__ = (
    "create_app",
    "default_rules",
    "LifespanHook",
    "Lifespan",
    "APIRouterCollection",
)
