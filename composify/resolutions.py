"""This module contains resolution mode for the dependency graph."""

from typing import Literal, TypeAlias

ResolutionMode: TypeAlias = Literal["exhaustive", "select_first"]
SELECT_FIRST: ResolutionMode = "select_first"
EXHAUSTIVE: ResolutionMode = "exhaustive"
DEFAULT_RESOLUTION_MODE: ResolutionMode = SELECT_FIRST

RESOLUTION_MODES = {EXHAUSTIVE, SELECT_FIRST}
