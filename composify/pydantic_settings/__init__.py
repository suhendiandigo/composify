"""Integration with pydantic_settings."""

from .rules import SettingsEnvSource, settings_rule

__all__ = ("settings_rule", "SettingsEnvSource")
