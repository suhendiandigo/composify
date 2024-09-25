from dataclasses import dataclass

from composify.metadata.qualifiers import BaseQualifierMetadata


@dataclass(frozen=True, slots=True)
class DisallowSubclass(BaseQualifierMetadata):
    disallow: bool = True

    def __bool__(self) -> bool:
        return self.disallow
