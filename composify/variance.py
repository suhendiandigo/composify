"""Module containing supported variance type."""

from typing import Literal, TypeAlias

__all__ = (
    "VarianceType",
    "INVARIANT",
    "COVARIANT",
    "CONTRAVARIANT",
)

VarianceType: TypeAlias = Literal["invariant", "covariant", "contravariant"]
INVARIANT = "invariant"
COVARIANT = "covariant"
CONTRAVARIANT = "contravariant"
