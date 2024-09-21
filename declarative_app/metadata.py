import sys
from dataclasses import dataclass

if sys.version_info < (3, 10):
    SLOTS = {}
else:
    SLOTS = {"slots": True}


class BaseMetadata:
    __slots__ = ()


@dataclass(frozen=True, **SLOTS)
class Name(BaseMetadata):
    name: str
