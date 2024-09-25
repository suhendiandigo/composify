from dataclasses import dataclass

from composify.metadata.qualifiers import BaseQualifierMetadata
from composify.resolutions import EXHAUSTIVE, SELECT_FIRST, ResolutionMode


@dataclass(frozen=True, slots=True)
class DisallowSubclass(BaseQualifierMetadata):
    disallow: bool = True

    def __bool__(self) -> bool:
        return self.disallow


@dataclass(frozen=True, slots=True)
class Resolution(BaseQualifierMetadata):
    """Allows for overriding the BlueprintResolver resolution mode."""

    mode: ResolutionMode


Exhaustive = Resolution(EXHAUSTIVE)
SelectFirst = Resolution(SELECT_FIRST)
