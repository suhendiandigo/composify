"""This module contains resolution mode for the dependency graph."""

from collections.abc import Sequence
from typing import Any, Literal, TypeAlias

ResolutionType: TypeAlias = Literal["exhaustive", "select_first", "unique"]
ResolutionMode: TypeAlias = ResolutionType | Sequence[ResolutionType]
SELECT_FIRST: ResolutionMode = "select_first"
EXHAUSTIVE: ResolutionMode = "exhaustive"
UNIQUE: ResolutionMode = "unique"
DEFAULT_RESOLUTION_MODE: ResolutionMode = UNIQUE

RESOLUTION_TYPES = {EXHAUSTIVE, UNIQUE, SELECT_FIRST}


def is_resolution_type(val: Any) -> bool:
    """Check if a value is a valid resolution type.

    Args:
        val (Any): Any value.

    Returns:
        bool: True if the value if a valid resolution type; otherwise False.
    """
    return val in RESOLUTION_TYPES


def is_resolution_mode(val: Any) -> bool:
    """Check if a value is a valid resolution mode.

    Args:
        val (Any): Any value

    Returns:
        bool: True if the value if a valid resolution mode; otherwise False.
    """
    if isinstance(val, str):
        return is_resolution_type(val)
    return all(is_resolution_type(v) for v in val)


def split_resolution(
    resolution: ResolutionMode,
) -> tuple[ResolutionType, ResolutionMode]:
    """Split a resolution more into current resolution and next resolution.

    Args:
        resolution (ResolutionMode): The resolution more to split.

    Raises:
        ValueError: If the resolution mode sequence is empty.

    Returns:
        tuple[ResolutionType, ResolutionMode]: Current resolution type to use and the next resolution mode.
    """
    if isinstance(resolution, str):
        return resolution, resolution
    if len(resolution) > 1:
        other = resolution[1:]
        if len(other) == 1:
            other = other[0]
        return resolution[0], other
    elif len(resolution) < 0:
        raise ValueError("Empty sequence for resolution mode.")
    return resolution[0], resolution[0]
