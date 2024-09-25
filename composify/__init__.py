"""Composify framework, simplify the development of declarative applications."""

__version__ = "0.1.0"


from .applications import Composify
from .container import Container
from .get import Get
from .get_or_create import AsyncGetOrCreate, GetOrCreate, ResolutionMode
from .injector import Injector
from .rules import collect_rules, rule

__all__ = [
    "Composify",
    "Container",
    "collect_rules",
    "rule",
    "Get",
    "ResolutionMode",
    "Injector",
    "ResolutionMode",
    "GetOrCreate",
    "AsyncGetOrCreate",
]
