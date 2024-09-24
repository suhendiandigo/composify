import asyncio
import inspect
from dataclasses import dataclass
from functools import partial, wraps
from types import FrameType, ModuleType
from typing import (
    Annotated,
    Any,
    Awaitable,
    Callable,
    Generic,
    Iterable,
    Mapping,
    ParamSpec,
    TypeAlias,
    TypeVar,
    get_origin,
    get_type_hints,
)

from composify.errors import (
    InvalidTypeAnnotation,
    MissingParameterTypeAnnotation,
    MissingReturnTypeAnnotation,
)
from composify.metadata import BaseAttributeMetadata, collect_attributes
from composify.metadata.attributes import AttributeSet
from composify.registry import (
    EntriesFilterer,
    EntriesValidator,
    Entry,
    Key,
    TypedRegistry,
)
from composify.types import get_type

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
    attributes: AttributeSet
    parameter_types: ParameterTypes

    @property
    def key(self) -> Key:
        return self.output_type

    @property
    def name(self) -> str:
        return self.canonical_name


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
        canonical_name=canonical_name,
        output_type=output_type,
        attributes=AttributeSet(output_attributes),
        parameter_types=parameter_types,
    )


def _ensure_type_annotation(
    *,
    type_annotation: type | None,
    name: str,
    raise_type: type[InvalidTypeAnnotation],
) -> type:
    if type_annotation is None:
        raise raise_type(f"{name} is missing a type annotation.")
    if not isinstance(type_annotation, type):
        origin = get_origin(type_annotation)
        if origin is not Annotated:
            raise raise_type(
                f"The annotation for {name} must be a type, got {type_annotation} of type {type(type_annotation)}."
            )
    return type_annotation


def rule_decorator(
    func: F,
) -> F | ConstructRule:
    func_params = inspect.signature(func).parameters
    func_id = f"@rule {func.__module__}:{func.__name__}"
    type_hints = get_type_hints(func, include_extras=True)
    return_type = _ensure_type_annotation(
        type_annotation=type_hints.get("return"),
        name=f"{func_id} return",
        raise_type=MissingReturnTypeAnnotation,
    )
    metadata = collect_attributes(return_type)
    return_type = get_type(return_type)

    parameter_types = tuple(
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


class RuleRegistry:

    __slots__ = "_rules"

    _rules: TypedRegistry[ConstructRule]

    def __init__(
        self,
        rules: Iterable[ConstructRule] | None = None,
        *,
        attribute_filterer: EntriesFilterer | None = None,
        unique_validator: EntriesValidator | None = None,
    ) -> None:
        self._rules = TypedRegistry(
            rules,
            entries_filterer=attribute_filterer,
            unique_validator=unique_validator,
        )

    def _compare_entries(
        self, entry: ConstructRule, other: ConstructRule
    ) -> bool:
        return entry == other

    def register_rule(self, rule: ConstructRule) -> None:
        self._rules.add_entry(rule)

    def register_rules(self, rules: Iterable[ConstructRule]) -> None:
        self._rules.add_entries(rules)

    def get(self, target: type[T]) -> Iterable[ConstructRule[T]]:
        return self._rules.get(target)
