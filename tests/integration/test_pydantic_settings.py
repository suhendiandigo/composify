from pydantic_settings import BaseSettings

from composify.applications import Composify
from composify.pydantic_settings import settings_rule
from composify.rules import collect_rules


@settings_rule
class ExampleSettings(BaseSettings, frozen=True):
    value: int = 5


rules = collect_rules()


def test_request_setting():
    composify = Composify(rules=rules)

    settings = composify.get_or_create.one(ExampleSettings)

    assert isinstance(settings, ExampleSettings)
    assert settings.value == 5
