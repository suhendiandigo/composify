import asyncio
import inspect
from bisect import insort
from dataclasses import dataclass
from functools import partial, wraps
from types import FrameType, ModuleType
from typing import (
    Any,
    Awaitable,
    Callable,
    FrozenSet,
    Generic,
    Iterable,
    Mapping,
    ParamSpec,
    TypeAlias,
    TypeVar,
    get_type_hints,
)

from declarative_app.metadata import BaseAttributeMetadata, get_attributes
from declarative_app.metadata.qualifiers import (
    VarianceType,
    get_qualifiers,
    resolve_variance,
)
from declarative_app.types import get_type, resolve_base_types

__all__ = ["rule", "as_rule"]


T = TypeVar("T")
P = ParamSpec("P")

SyncRuleFunctionType: TypeAlias = Callable[P, T]
AsyncRuleFunctionType: TypeAlias = Callable[P, Awaitable[T]]
RuleFunctionType: TypeAlias = SyncRuleFunctionType | AsyncRuleFunctionType

F = TypeVar("F", bound=RuleFunctionType)

RULE_ATTR = "__rule__"

ParameterType: TypeAlias = tuple[str, type]
ParameterTypes: TypeAlias = frozenset[ParameterType]


@dataclass(frozen=True)
class ConstructRule(Generic[T]):
    function: RuleFunctionType
    is_async: bool
    cannonical_name: str
    output_type: type[T]
    output_attributes: FrozenSet[BaseAttributeMetadata]
    parameter_types: ParameterTypes


def _make_rule(
    func: RuleFunctionType,
    *,
    is_async: bool,
    canonical_name: str,
    output_type: type,
    output_attributes: Iterable[BaseAttributeMetadata],
    parameter_types: ParameterTypes,
) -> ConstructRule:
    return ConstructRule(
        func,
        is_async=is_async,
        cannonical_name=canonical_name,
        output_type=output_type,
        output_attributes=frozenset(output_attributes),
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
    type_annotation: type | None,
    name: str,
    raise_type: type[InvalidTypeAnnotation],
) -> type:
    if type_annotation is None:
        raise raise_type(f"{name} is missing a type annotation.")
    # if not isinstance(type_annotation, type):
    #     raise raise_type(
    #         f"The annotation for {name} must be a type, got {type_annotation} of type {type(type_annotation)}."
    #     )
    return type_annotation


def rule_decorator(
    func: F,
    *,
    return_rule: bool = False,
) -> F | ConstructRule:
    func_params = inspect.signature(func).parameters
    func_id = f"@rule {func.__module__}:{func.__name__}"
    type_hints = get_type_hints(func, include_extras=True)
    return_type = _ensure_type_annotation(
        type_annotation=type_hints.get("return"),
        name=f"{func_id} return",
        raise_type=MissingReturnTypeAnnotation,
    )
    metadata = get_attributes(return_type)
    return_type = get_type(return_type)

    parameter_types = frozenset(
        (
            parameter,
            _ensure_type_annotation(
                type_annotation=type_hints.get(parameter),
                name=f"{func_id} parameter {parameter}",
                raise_type=MissingParameterTypeAnnotation,
            ),
        )
        for parameter in func_params
    )
    effective_name = f"{func.__module__}.{func.__qualname__}".replace(
        ".<locals>", ""
    )

    rule = _make_rule(
        func,
        is_async=asyncio.iscoroutinefunction(func),
        canonical_name=effective_name,
        output_type=return_type,
        output_attributes=metadata,
        parameter_types=parameter_types,
    )
    setattr(
        func,
        RULE_ATTR,
        rule,
    )
    if return_rule:
        return rule
    return func


@wraps(rule_decorator)
def rule(f: RuleFunctionType | None = None, /, **kwargs):
    if f is None:
        return partial(rule_decorator, **kwargs)
    return rule_decorator(f, **kwargs)


def as_rule(f: Any) -> ConstructRule | None:
    if isinstance(f, ConstructRule):
        return f
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
                if isinstance(item, ConstructRule):
                    yield item
                else:
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


class DuplicateRuleError(RuleError):
    def __init__(self, to_add: ConstructRule, existing: ConstructRule) -> None:
        self.to_add = to_add
        self.existing = existing
        super().__init__(
            f"Rule {to_add!r} conflict with existing rule {existing!r}"
        )


def _rule_ordering(rule: ConstructRule) -> int:
    return len(rule.output_type.mro())


class RuleRegistry:

    __slots__ = ("_rules", "_default_variance")

    _rules: dict[type, list[ConstructRule]]

    def __init__(
        self,
        rules: Iterable[ConstructRule],
        default_variance: VarianceType = "covariant",
    ) -> None:
        self._rules = {}
        self._default_variance = default_variance
        for rule in rules:
            self.register_rule(rule)

    def _register_rule_to_type(self, type_: type, rule: ConstructRule) -> None:
        if type_ in self._rules:
            rules = self._rules[type_]
            for _rule in rules:
                if _rule == rule:
                    raise DuplicateRuleError(rule, _rule)
                if (_rule.parameter_types == rule.parameter_types) and (
                    _rule.output_attributes == rule.output_attributes
                ):
                    raise RuleSignatureConflictError(rule, _rule)
            # We want to keep the rules ordered
            # by how derived the output type is
            # we are prioritizing the less derived type
            insort(rules, rule, key=_rule_ordering)
        else:
            self._rules[type_] = [rule]

    def register_rule(self, rule: ConstructRule) -> None:
        for type_ in resolve_base_types(rule.output_type):
            self._register_rule_to_type(type_, rule)

    def register_rules(self, rules: Iterable[ConstructRule]) -> None:
        for rule in rules:
            self.register_rule(rule)

    def _get_rule_for_type(
        self, type_: type[T], variance: VarianceType
    ) -> list[ConstructRule[T]]:
        if variance == "invariant":
            return list(
                filter(
                    lambda x: x.output_type is type_,
                    self._rules.get(type_, []),
                )
            )
        elif variance == "contravariant":
            rules = set()
            for parent_type in resolve_base_types(type_):
                for rule in self._rules.get(parent_type, tuple()):
                    rules.add(rule)
            return list(rules)
        return self._rules.get(type_, [])

    def get(self, target: type[T]) -> Iterable[ConstructRule[T]] | None:
        type_ = get_type(target)
        attributes = get_attributes(target)
        qualifiers = get_qualifiers(target)

        variance = resolve_variance(qualifiers, self._default_variance)

        rules: list[ConstructRule[T]] = self._get_rule_for_type(
            type_, variance
        )
        if not rules:
            return None
        if attributes and (
            filtered := [
                rule
                for rule in rules
                if rule.output_attributes.issuperset(attributes)
            ]
        ):
            return filtered
        return rules
