from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

from .base import SLOTS, BaseMetadata, TypeMetadataPair, _get_metadata


class BaseQualifierMetadata(BaseMetadata):
    pass


TypeQualifierPair: TypeAlias = TypeMetadataPair[BaseQualifierMetadata]

VarianceType = Literal["invariant", "covariant", "contravariant"]


@dataclass(frozen=True, **SLOTS)
class Variance(BaseQualifierMetadata):
    name: VarianceType = "covariant"


Invariant = Variance("invariant")
Covariant = Variance("covariant")
Contravariant = Variance("contravariant")


def _is_qualifier_instance(val: Any) -> bool:
    return isinstance(val, BaseQualifierMetadata)


def get_qualifiers(type_: type) -> TypeQualifierPair:
    return _get_metadata(type_, _is_qualifier_instance)
