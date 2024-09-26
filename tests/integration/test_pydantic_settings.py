from pydantic_settings import BaseSettings

from composify.applications import Composify
from composify.pydantic_settings import PydanticSettingsProvider


class ExampleSettings(BaseSettings, frozen=True):
    value: int = 5


def test_request_setting():
    composify = Composify(providers=[PydanticSettingsProvider()])

    settings = composify.get_or_create.one(ExampleSettings)

    assert isinstance(settings, ExampleSettings)
    assert settings.value == 5
