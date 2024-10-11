"""This module contains resolution mode for the dependency graph."""

from collections.abc import Sequence
from typing import Any, Literal, TypeAlias

ResolutionType: TypeAlias = Literal["exhaustive", "select_first", "unique"]
SELECT_FIRST: ResolutionType = "select_first"
EXHAUSTIVE: ResolutionType = "exhaustive"
UNIQUE: ResolutionType = "unique"

RESOLUTION_TYPES = {EXHAUSTIVE, UNIQUE, SELECT_FIRST}

ResolutionMode: TypeAlias = ResolutionType | Sequence[ResolutionType]
DEFAULT_RESOLUTION_MODE: ResolutionMode = UNIQUE


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
            return resolution[0], other[0]
        return resolution[0], other
    elif len(resolution) < 0:
        raise ValueError("Empty sequence for resolution mode.")
    return resolution[0], resolution[0]


def join_resolution(
    resolution1: ResolutionMode, resolution2: ResolutionMode
) -> ResolutionMode:
    """Join 2 resolutions into a single resolution.

    Args:
        resolution1 (ResolutionMode): The header of the resolution.
        resolution2 (ResolutionMode): The tail of the resolution.

    Returns:
        ResolutionMode: A single joined resolution.
    """
    if isinstance(resolution1, str) and isinstance(resolution2, str):
        return (resolution1, resolution2)
    elif isinstance(resolution1, str) and isinstance(resolution2, Sequence):
        return (resolution1, *resolution2)
    elif isinstance(resolution1, Sequence) and isinstance(resolution2, str):
        return (*resolution1, resolution2)
    return (*resolution1, *resolution2)
