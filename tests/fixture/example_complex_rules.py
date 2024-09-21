from dataclasses import dataclass

from declarative_app.rules import collect_rules, rule


@dataclass(frozen=True)
class Param:
    value: int


@dataclass(frozen=True)
class Param1:
    value: int


@dataclass(frozen=True)
class Param2:
    value: int


@dataclass(frozen=True)
class Result:
    value: int


@rule
def infer_param_1(param: Param) -> Param1:
    return Param1(param.value * 2)


@rule
def infer_param_2(param: Param) -> Param2:
    return Param2(param.value * 3)


@rule
def create_result(param1: Param1, param2: Param2) -> Result:
    return Result(param1.value + param2.value)


DEFAULT_VALUE = 1


@rule
def default_param() -> Param:
    return Param(DEFAULT_VALUE)


rules = collect_rules()
