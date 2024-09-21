from dataclasses import dataclass

from declarative_app.rules import collect_rules, rule


@dataclass(frozen=True)
class Param:
    value: str


@dataclass(frozen=True)
class Param1:
    value: str


@dataclass(frozen=True)
class Result:
    value: str


@rule
def example_sync_rule(param: Param) -> Result:
    return Result(param.value)


DEFAULT_VALUE = "this is the default"


@rule
def default_param() -> Param:
    return Param(DEFAULT_VALUE)


rules = collect_rules()
