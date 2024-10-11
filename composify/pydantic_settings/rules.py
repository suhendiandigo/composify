"""Module containing the rules creation for pydantic settings."""

from dataclasses import dataclass
from functools import partial
from typing import TypeVar

from pydantic_core import ValidationError
from pydantic_settings import BaseSettings
from pydantic_settings.sources import DotenvType

from composify.rules import ConstructRuleSet, attach_rule, rule


@dataclass(frozen=True)
class SettingsEnvSource:
    """Create a rule for this type to override the env source used when creating instances of BaseSettings."""

    env_file: DotenvType


T = TypeVar("T", bound=type[BaseSettings])


def _wrapper(cls: T, *, is_optional: bool):
    if is_optional:

        def create_settings() -> T | None:
            try:
                return cls()
            except ValidationError:
                return None

        def create_settings_from_env(env: SettingsEnvSource) -> T | None:
            try:
                return cls(_env_file=env.env_file)
            except ValidationError:
                return None

        attach_rule(
            cls,
            ConstructRuleSet(
                (
                    rule(
                        create_settings_from_env,
                        priority=0,
                        name=f"optional_create_{cls.__module__}.{cls.__name__}_from_env",
                        return_type=cls,
                        is_optional=True,
                    ),
                    rule(
                        create_settings,
                        priority=-1,
                        name=f"optional_create_{cls.__module__}.{cls.__name__}",
                        return_type=cls,
                        is_optional=True,
                    ),
                )
            ),
        )
    else:

        def create_settings() -> T:
            return cls()

        def create_settings_from_env(env: SettingsEnvSource) -> T:
            return cls(_env_file=env.env_file)

        attach_rule(
            cls,
            ConstructRuleSet(
                (
                    rule(
                        create_settings_from_env,
                        priority=0,
                        name=f"create_{cls.__module__}.{cls.__name__}_from_env",
                        return_type=cls,
                    ),
                    rule(
                        create_settings,
                        priority=-1,
                        name=f"create_{cls.__module__}.{cls.__name__}",
                        return_type=cls,
                    ),
                )
            ),
        )

    return cls


def settings_rule(cls: T | None = None, *, is_optional: bool = False) -> T:
    """Create a rule to automatically create an instance of the base settings type.

    Args:
        cls (T | None, optional): The base setting class to create rule for. Defaults to None.
        is_optional (bool, optional): Set the settings to be optional. Defaults to False.

    Returns:
        T: Returns the input type.
    """
    if cls is None:
        return partial(
            _wrapper,
            is_optional=is_optional,
        )

    return _wrapper(cls, is_optional=is_optional)
