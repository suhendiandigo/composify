from dataclasses import dataclass
from typing import Literal

from .base import SLOTS, BaseMetadata, MetadataSet, _collect_metadata


class BaseQualifierMetadata(BaseMetadata):
    pass


class QualifierSet(MetadataSet[BaseQualifierMetadata]):
    pass


def collect_qualifiers(type_: type) -> QualifierSet:
    """Collect all annotated metadata that inherits BaseQualifierMetadata class as a frozenset."""
    return _collect_metadata(type_, BaseQualifierMetadata, QualifierSet)


VarianceType = Literal["invariant", "covariant", "contravariant"]


@dataclass(frozen=True, **SLOTS)
class Variance(BaseQualifierMetadata):
    variance: VarianceType = "covariant"

    @staticmethod
    def resolve(
        qualifiers: QualifierSet,
        default_variance: VarianceType = "invariant",
    ) -> VarianceType:
        try:
            return qualifiers[Variance].variance
        except KeyError:
            return default_variance


Invariant = Variance("invariant")
Covariant = Variance("covariant")
Contravariant = Variance("contravariant")


@dataclass(frozen=True, **SLOTS)
class DisallowSubclass(BaseQualifierMetadata):
    disallow: bool = True

    def __bool__(self) -> bool:
        return self.disallow
