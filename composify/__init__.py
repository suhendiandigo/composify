"""Composify framework, simplify the development of declarative applications."""

__version__ = "0.1.0"


from .applications import AsyncComposify, Composify
from .container import Container
from .get import Get
from .get_or_create import AsyncGetOrCreate, GetOrCreate, ResolutionMode
from .injector import AsyncInjector, Injector
from .rules import collect_rules, rule

__all__ = [
    "Composify",
    "AsyncComposify",
    "Container",
    "collect_rules",
    "rule",
    "Get",
    "ResolutionMode",
    "Injector",
    "AsyncInjector",
    "ResolutionMode",
    "GetOrCreate",
    "AsyncGetOrCreate",
]
