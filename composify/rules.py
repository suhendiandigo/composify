"""This modules contains the backbone @rule decorator.

Example:
    from composify import collect_rules, rule

    @rule
    def create_default() -> int:
        return 1

    rules = collect_rules()

    print(len(rules) == 1)
    #> True

"""

import asyncio
import inspect
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from functools import partial
from types import FrameType, ModuleType
from typing import (
    Annotated,
    Any,
    Generic,
    ParamSpec,
    TypeAlias,
    TypeVar,
    get_type_hints,
)

from composify._helper import ensure_type_annotation, resolve_type_name
from composify._registry import (
    EntriesCollator,
    EntriesFilterer,
    Entry,
    Key,
    TypedRegistry,
)
from composify.errors import (
    MissingParameterTypeAnnotation,
    MissingReturnTypeAnnotation,
)
from composify.metadata import AttributeSet, collect_attributes
from composify.metadata.qualifiers import BaseQualifierMetadata
from composify.types import AnnotatedType

__all__ = ("rule", "as_rule")


T = TypeVar("T")
P = ParamSpec("P")

SyncRuleFunctionType: TypeAlias = Callable[P, T]
AsyncRuleFunctionType: TypeAlias = Callable[P, Awaitable[T]]
RuleFunctionType: TypeAlias = (
    SyncRuleFunctionType | AsyncRuleFunctionType | type
)

F = TypeVar("F", bound=RuleFunctionType)

RULE_ATTR = "__rule__"

ParameterType: TypeAlias = tuple[str, AnnotatedType]
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
    is_optional: bool

    @property
    def key(self) -> Key:
        return self.output_type

    @property
    def name(self) -> str:
        return self.canonical_name


class ConstructRuleSet(tuple[ConstructRule, ...]):
    pass


def _add_qualifiers(
    type_: AnnotatedType[T], qualifiers: Iterable[BaseQualifierMetadata] | None
) -> AnnotatedType[T]:
    if qualifiers is not None:
        for qualifier in qualifiers:
            type_ = Annotated[type_, qualifier]
    return type_


def _get_init_func(cls: type):
    if cls.__init__ == object.__init__:  # type: ignore[misc]
        func = cls
        func_params = []
    else:
        func = cls.__init__  # type: ignore[misc]
        func_params = list(inspect.signature(func).parameters)[1:]
    return func, func_params


def attach_rule(value: Any, rule: ConstructRule | ConstructRuleSet) -> None:
    """Attach a rule to an object that is collectible via collect_rules().
    To be used with custom rule decorators.

    Args:
        value (Any): The object to attach the rule to.
        rule (ConstructRule | ConstructRuleSet): The rule to attach.
    """
    setattr(
        value,
        RULE_ATTR,
        rule,
    )


def _rule_decorator(
    decorated: F,
    *,
    priority: int,
    name: str | None = None,
    dependency_qualifiers: Iterable[BaseQualifierMetadata] | None = None,
    return_type: type | None = None,
    is_optional: bool | None = None,
) -> F:
    if inspect.isclass(decorated):
        func, func_params = _get_init_func(decorated)
    else:
        func = decorated
        func_params = list(inspect.signature(func).parameters)
    name = name or f"{func.__module__}:{func.__name__}"
    func_id = f"@rule {name}"
    type_hints = get_type_hints(func, include_extras=True)
    return_type = return_type or (
        decorated if inspect.isclass(decorated) else type_hints.get("return")
    )
    return_type_info = ensure_type_annotation(
        type_annotation=return_type,
        name=f"{func_id} return",
        raise_type=MissingReturnTypeAnnotation,
    )
    is_optional = is_optional or return_type_info.is_optional
    metadata = collect_attributes(return_type_info)

    parameter_types: tuple[tuple[str, AnnotatedType], ...] = tuple(
        (
            parameter,
            _add_qualifiers(
                ensure_type_annotation(
                    type_annotation=type_hints.get(parameter),
                    name=f"{func_id} parameter {parameter}",
                    raise_type=MissingParameterTypeAnnotation,
                ).annotation,
                dependency_qualifiers,
            ),
        )
        for parameter in func_params
    )
    effective_name = resolve_type_name(decorated)

    rule: ConstructRule = ConstructRule(
        decorated,
        is_async=asyncio.iscoroutinefunction(func),
        canonical_name=effective_name,
        output_type=return_type_info.inner_type,
        attributes=metadata,
        parameter_types=parameter_types,
        priority=priority,
        is_optional=is_optional,
    )
    attach_rule(decorated, rule)
    return decorated


def rule(
    f: RuleFunctionType | None = None,
    /,
    *,
    priority: int = 0,
    name: str | None = None,
    dependency_qualifiers: Iterable[BaseQualifierMetadata] | None = None,
    return_type: type | None = None,
    is_optional: bool | None = None,
):
    """Marks a function or a class as a rule. Allowing collection via collect_rules().

    Args:
        f (RuleFunctionType | None, optional): The function or class to mark as a rule. Defaults to None.
        name (str | None, optional): Override the name of the rule if exists.
        priority (int, optional): The resolution priority. Higher value equals higher priority. Defaults to 0.
        dependency_qualifiers (Iterable[BaseQualifierMetadata] | None, optional): Add qualifiers to all dependencies. Defaults to None.
        return_type (type | None, optional): Override the return type of the rule.
        is_optional (bool | None, optional): Override the optionality of the rule.

    Returns:
        The input function or class.

    Raises:
        MissingReturnTypeAnnotation: Raised if the return type annotation is missing.
        MissingParameterTypeAnnotation: Raised if there are any missing type annotation from parameter.
        DuplicatedEntryError: Raised if there are duplicated rule.

    """
    if f is None:
        return partial(
            _rule_decorator,
            priority=priority,
            name=name,
            dependency_qualifiers=dependency_qualifiers,
            return_type=return_type,
            is_optional=is_optional,
        )
    return _rule_decorator(
        f,
        priority=priority,
        name=name,
        dependency_qualifiers=dependency_qualifiers,
        return_type=return_type,
        is_optional=is_optional,
    )


def as_rule(f: Any) -> ConstructRule:
    """Returns the ConstructRule associated with the object.

    Args:
        f (Any): The object to cast as ConstructRule.

    Returns:
        ConstructRule | None: Returns the ConstructRule if the object has been marked with @rule; otherwise None.
    """
    if isinstance(f, ConstructRule):
        return f
    r = getattr(f, RULE_ATTR, None)
    if r is None:
        raise TypeError(f"{f} is not a rule.")
    return r


def _extract_rules(rule: ConstructRule | ConstructRuleSet):
    if isinstance(rule, ConstructRule):
        yield rule
    elif isinstance(rule, ConstructRuleSet):
        for r in rule:
            yield from _extract_rules(r)
    else:
        if not callable(rule):
            return
        rule = getattr(rule, RULE_ATTR, None)
        yield from _extract_rules(rule)


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
                yield from _extract_rules(item)

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


class AsyncRuleNotAllowedError(RuleError):
    def __init__(self, rule: ConstructRule) -> None:
        self.rule = rule
        super().__init__(f"Async rule is not allowed for registry: {rule!r}.")


class RuleRegistry:
    __slots__ = ("_rules", "_allows_async")

    _rules: TypedRegistry[ConstructRule]

    def __init__(
        self,
        rules: Iterable[ConstructRule] | None = None,
        *,
        attribute_filterer: EntriesFilterer | None = None,
        entries_collator: EntriesCollator | None = None,
        allows_async: bool = True,
    ) -> None:
        self._rules = TypedRegistry(
            rules,
            entries_filterer=attribute_filterer,
            entries_collator=entries_collator,
        )
        self._allows_async = allows_async

    @property
    def allows_async(self) -> bool:
        return self._allows_async

    def _compare_entries(
        self, entry: ConstructRule, other: ConstructRule
    ) -> bool:
        return entry == other

    def register_rule(self, rule: ConstructRule) -> None:
        if rule.is_async and not self.allows_async:
            raise AsyncRuleNotAllowedError(rule)
        self._rules.add_entry(rule)

    def register_rules(self, rules: Iterable[ConstructRule]) -> None:
        for rule in rules:
            self.register_rule(rule)

    def get(self, target: AnnotatedType[T]) -> Iterable[ConstructRule[T]]:
        return self._rules.get(target)
