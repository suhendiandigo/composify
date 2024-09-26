"""This module contains resolution mode for the dependency graph."""

from typing import Literal, TypeAlias

ResolutionMode: TypeAlias = Literal["exhaustive", "select_first", "unique"]
SELECT_FIRST: ResolutionMode = "select_first"
EXHAUSTIVE: ResolutionMode = "exhaustive"
UNIQUE: ResolutionMode = "unique"
DEFAULT_RESOLUTION_MODE: ResolutionMode = UNIQUE

RESOLUTION_MODES = {EXHAUSTIVE, UNIQUE, SELECT_FIRST}
