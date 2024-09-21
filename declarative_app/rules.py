import asyncio
import inspect
from dataclasses import dataclass
from types import FrameType, ModuleType
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Iterable,
    Mapping,
    ParamSpec,
    Type,
    TypeVar,
    get_type_hints,
)

from typing_extensions import TypeAlias

__all__ = ["rule", "as_rule"]


T = TypeVar("T")
P = ParamSpec("P")

SyncRuleFunctionType: TypeAlias = Callable[P, T]
AsyncRuleFunctionType: TypeAlias = Callable[P, Awaitable[T]]
RuleFunctionType: TypeAlias = SyncRuleFunctionType | AsyncRuleFunctionType

RULE_ATTR = "__rule__"


@dataclass(frozen=True)
class ConstructRule(Generic[T]):
    function: RuleFunctionType
    is_async: bool
    cannonical_name: str
    output_type: type[T]
    parameter_types: Mapping[str, type]


def _make_rule(
    func: RuleFunctionType,
    *,
    is_async: bool,
    canonical_name: str,
    output_type: Type,
    parameter_types: Mapping[str, Type],
) -> ConstructRule:
    return ConstructRule(
        func,
        is_async=is_async,
        cannonical_name=canonical_name,
        output_type=output_type,
        parameter_types=parameter_types,
    )


class InvalidTypeAnnotation(TypeError):
    pass


class MissingReturnTypeAnnotation(InvalidTypeAnnotation):
    pass


class MissingParameterTypeAnnotation(InvalidTypeAnnotation):
    pass


def _ensure_type_annotation(
    *,
    type_annotation: Type | None,
    name: str,
    raise_type: Type[InvalidTypeAnnotation],
) -> Type:
    if type_annotation is None:
        raise raise_type(f"{name} is missing a type annotation.")
    if not isinstance(type_annotation, type):
        raise raise_type(
            f"The annotation for {name} must be a type, got {type_annotation} of type {type(type_annotation)}."
        )
    return type_annotation


def rule_decorator(func):
    func_params = inspect.signature(func).parameters
    func_id = f"@rule {func.__module__}:{func.__name__}"
    type_hints = get_type_hints(func, include_extras=True)
    return_type = _ensure_type_annotation(
        type_annotation=type_hints.get("return"),
        name=f"{func_id} return",
        raise_type=MissingReturnTypeAnnotation,
    )

    parameter_types = {
        parameter: _ensure_type_annotation(
            type_annotation=type_hints.get(parameter),
            name=f"{func_id} parameter {parameter}",
            raise_type=MissingParameterTypeAnnotation,
        )
        for parameter in func_params
    }
    effective_name = f"{func.__module__}.{func.__qualname__}".replace(
        ".<locals>", ""
    )

    setattr(
        func,
        RULE_ATTR,
        _make_rule(
            func,
            is_async=asyncio.iscoroutinefunction(func),
            canonical_name=effective_name,
            output_type=return_type,
            parameter_types=parameter_types,
        ),
    )
    return func


def rule(f: RuleFunctionType | None = None):
    if f is None:
        return rule_decorator
    return rule_decorator(f)


def as_rule(f: Any) -> ConstructRule | None:
    return getattr(f, RULE_ATTR, None)


def collect_rules(
    *namespaces: ModuleType | Mapping[str, Any]
) -> Iterable[ConstructRule]:
    if not namespaces:
        currentframe = inspect.currentframe()
        assert isinstance(currentframe, FrameType)
        caller_frame = currentframe.f_back
        assert isinstance(caller_frame, FrameType)

        global_items = caller_frame.f_globals
        namespaces = (global_items,)

    def iter_rules():
        for namespace in namespaces:
            mapping = (
                namespace.__dict__
                if isinstance(namespace, ModuleType)
                else namespace
            )
            for item in mapping.values():
                if not callable(item):
                    continue
                rule = getattr(item, RULE_ATTR, None)
                if isinstance(rule, ConstructRule):
                    yield rule

    return list(iter_rules())


class RuleError(Exception):
    pass


class RuleSignatureConflictError(RuleError):
    def __init__(self, to_add: ConstructRule, existing: ConstructRule) -> None:
        self.to_add = to_add
        self.existing = existing
        super().__init__(
            f"Rule {to_add!r} conflict with existing rule {existing!r}"
        )


class RuleRegistry:

    __slots__ = "_rules"

    _rules: dict[type, list[ConstructRule]]

    def __init__(self, rules: Iterable[ConstructRule]) -> None:
        self._rules = {}
        for rule in rules:
            self.register_rule(rule)

    def register_rule(self, rule: ConstructRule) -> None:
        type_ = rule.output_type
        if type_ in self._rules:
            rules = self._rules[type_]
            for _rule in rules:
                if _rule.parameter_types == rule.parameter_types:
                    raise RuleSignatureConflictError(rule, _rule)
            rules.append(rule)
        else:
            self._rules[type_] = [rule]

    def register_rules(self, rules: Iterable[ConstructRule]) -> None:
        for rule in rules:
            self.register_rule(rule)

    def get(self, type_: type[T]) -> list[ConstructRule[T]] | None:
        return self._rules.get(type_, None)
