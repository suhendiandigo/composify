from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

from .base import SLOTS, BaseMetadata, MetadataSet, _get_metadata


class BaseQualifierMetadata(BaseMetadata):
    pass


QualifierSet: TypeAlias = MetadataSet[BaseQualifierMetadata]


def _is_qualifier_instance(val: Any) -> bool:
    return isinstance(val, BaseQualifierMetadata)


def get_qualifiers(type_: type) -> QualifierSet:
    return _get_metadata(type_, _is_qualifier_instance)


VarianceType = Literal["invariant", "covariant", "contravariant"]


@dataclass(frozen=True, **SLOTS)
class Variance(BaseQualifierMetadata):
    variance: VarianceType = "covariant"


Invariant = Variance("invariant")
Covariant = Variance("covariant")
Contravariant = Variance("contravariant")


def resolve_variance(
    qualifiers: QualifierSet,
    default_variance: VarianceType = "invariant",
) -> VarianceType:
    variance = None
    for qualifier in qualifiers:
        if isinstance(qualifier, Variance):
            variance = qualifier.variance
            break
    if variance is None:
        return default_variance
    return variance
