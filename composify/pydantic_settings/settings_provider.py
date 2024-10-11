"""Supports for pydantic_settings.BaseSettings."""

from collections.abc import Iterable

from pydantic_core import ValidationError
from pydantic_settings import BaseSettings

from composify._helper import resolve_type_name
from composify.constructor import Constructor
from composify.provider import ConstructorProvider, Static
from composify.types import AnnotatedType, get_type


class PydanticSettingsProvider(ConstructorProvider):
    """This provider generate constructor for all pydantic_settings.BaseSettings types."""

    def __init__(
        self, env_file: str | None = None, name: str | None = None
    ) -> None:
        super().__init__()
        self._env_file = env_file
        self._name = name or f"pydantic_settings::{env_file or 'ENV'}"

    def provide_for_type(self, type_: AnnotatedType) -> Iterable[Constructor]:
        """Provide constructor for a specific type.

        Args:
            type_ (AnnotatedType): The type to provide for.

        Returns:
            Iterable[Constructor]: Iterable of constructor matching the type_.

        """
        type_ = get_type(type_)
        if issubclass(type_, BaseSettings):
            try:
                settings = type_(_env_file=self._env_file)
            except ValidationError:
                return
            yield Constructor(
                source=f"{self._name}_{resolve_type_name(type_)}",
                constructor=Static(settings),
                is_async=False,
                output_type=type_,
                dependencies=(),
                is_optional=False,
            )
