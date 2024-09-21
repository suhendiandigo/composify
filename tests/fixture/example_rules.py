from dataclasses import dataclass

from declarative_app.rules import collect_rules, rule


@dataclass(frozen=True)
class Param:
    value: str


@dataclass(frozen=True)
class Result:
    value: str


@rule
async def example_async_rule(param: Param) -> Result:
    return Result(param.value)


@rule
def example_sync_rule(param: Param) -> Result:
    return Result(param.value)


rules = collect_rules()
