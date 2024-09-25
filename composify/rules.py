import asyncio
import inspect
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from functools import partial, wraps
from types import FrameType, ModuleType
from typing import Any, Generic, ParamSpec, TypeAlias, TypeVar, get_type_hints

from composify.errors import (
    MissingParameterTypeAnnotation,
    MissingReturnTypeAnnotation,
)
from composify.metadata import collect_attributes
from composify.metadata.attributes import AttributeSet
from composify.registry import (
    EntriesCollator,
    EntriesFilterer,
    Entry,
    Key,
    TypedRegistry,
)
from composify.types import (
    AnnotatedType,
    ensure_type_annotation,
    get_type,
    resolve_type_name,
)

__all__ = ["rule", "as_rule"]


T = TypeVar("T")
P = ParamSpec("P")

SyncRuleFunctionType: TypeAlias = Callable[P, T]
AsyncRuleFunctionType: TypeAlias = Callable[P, Awaitable[T]]
RuleFunctionType: TypeAlias = SyncRuleFunctionType | AsyncRuleFunctionType

F = TypeVar("F", bound=RuleFunctionType)

RULE_ATTR = "__rule__"

ParameterType: TypeAlias = tuple[str, type]
ParameterTypes: TypeAlias = tuple[ParameterType, ...]


@dataclass(frozen=True)
class ConstructRule(Entry, Generic[T]):
    function: RuleFunctionType
    is_async: bool
    canonical_name: str
    output_type: type[T]
    parameter_types: ParameterTypes
    attributes: AttributeSet
    priority: int

    @property
    def key(self) -> Key:
        return self.output_type

    @property
    def name(self) -> str:
        return self.canonical_name


def rule_decorator(
    func: F,
    *,
    priority: int,
) -> F | ConstructRule:
    func_params = inspect.signature(func).parameters
    func_id = f"@rule {func.__module__}:{func.__name__}"
    type_hints = get_type_hints(func, include_extras=True)
    return_type = ensure_type_annotation(
        type_annotation=type_hints.get("return"),
        name=f"{func_id} return",
        raise_type=MissingReturnTypeAnnotation,
    )
    metadata = collect_attributes(return_type)
    return_type = get_type(return_type)

    parameter_types = tuple(
        (
            parameter,
            ensure_type_annotation(
                type_annotation=type_hints.get(parameter),
                name=f"{func_id} parameter {parameter}",
                raise_type=MissingParameterTypeAnnotation,
            ),
        )
        for parameter in func_params
    )
    effective_name = resolve_type_name(func)

    rule = ConstructRule(
        func,
        is_async=asyncio.iscoroutinefunction(func),
        canonical_name=effective_name,
        output_type=return_type,
        attributes=metadata,
        parameter_types=parameter_types,
        priority=priority,
    )
    setattr(
        func,
        RULE_ATTR,
        rule,
    )
    return func


@wraps(rule_decorator)
def rule(
    f: RuleFunctionType | None = None,
    /,
    *,
    priority: int = 0,
):
    if f is None:
        return partial(rule_decorator, priority=priority)
    return rule_decorator(f, priority=priority)


def as_rule(f: Any) -> ConstructRule | None:
    if isinstance(f, ConstructRule):
        return f
    return getattr(f, RULE_ATTR, None)


def collect_rules(
    *namespaces: ModuleType | Mapping[str, Any],
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


class RuleRegistry:
    __slots__ = "_rules"

    _rules: TypedRegistry[ConstructRule]

    def __init__(
        self,
        rules: Iterable[ConstructRule] | None = None,
        *,
        attribute_filterer: EntriesFilterer | None = None,
        entries_collator: EntriesCollator | None = None,
    ) -> None:
        self._rules = TypedRegistry(
            rules,
            entries_filterer=attribute_filterer,
            entries_collator=entries_collator,
        )

    def _compare_entries(
        self, entry: ConstructRule, other: ConstructRule
    ) -> bool:
        return entry == other

    def register_rule(self, rule: ConstructRule) -> None:
        self._rules.add_entry(rule)

    def register_rules(self, rules: Iterable[ConstructRule]) -> None:
        self._rules.add_entries(rules)

    def get(self, target: AnnotatedType[T]) -> Iterable[ConstructRule[T]]:
        return self._rules.get(target)
