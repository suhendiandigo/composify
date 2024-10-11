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

__all__ = ["rule", "as_rule"]


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


def _rule_decorator(
    decorated: F,
    *,
    priority: int,
    dependency_qualifiers: Iterable[BaseQualifierMetadata] | None = None,
) -> F:
    if inspect.isclass(decorated):
        func, func_params = _get_init_func(decorated)
    else:
        func = decorated
        func_params = list(inspect.signature(func).parameters)
    func_id = f"@rule {func.__module__}:{func.__name__}"
    type_hints = get_type_hints(func, include_extras=True)
    return_type = ensure_type_annotation(
        type_annotation=decorated
        if inspect.isclass(decorated)
        else type_hints.get("return"),
        name=f"{func_id} return",
        raise_type=MissingReturnTypeAnnotation,
    )
    is_optional = return_type.is_optional
    metadata = collect_attributes(return_type)
    return_type = return_type.inner_type

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
        output_type=return_type,
        attributes=metadata,
        parameter_types=parameter_types,
        priority=priority,
        is_optional=is_optional,
    )
    setattr(
        decorated,
        RULE_ATTR,
        rule,
    )
    return decorated


def rule(
    f: RuleFunctionType | None = None,
    /,
    *,
    priority: int = 0,
    dependency_qualifiers: Iterable[BaseQualifierMetadata] | None = None,
):
    """Marks a function or a class as a rule. Allowing collection via collect_rules().

    Args:
        f (RuleFunctionType | None, optional): The function or class to mark as a rule. Defaults to None.
        priority (int, optional): The resolution priority. Higher value equals higher priority. Defaults to 0.
        dependency_qualifiers (Iterable[BaseQualifierMetadata] | None, optional): Add qualifiers to all dependencies. Defaults to None.

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
            dependency_qualifiers=dependency_qualifiers,
        )
    return _rule_decorator(
        f, priority=priority, dependency_qualifiers=dependency_qualifiers
    )


def as_rule(f: Any) -> ConstructRule | None:
    """Returns the ConstructRule associated with the object.

    Args:
        f (Any): The object to cast as ConstructRule.

    Returns:
        ConstructRule | None: Returns the ConstructRule if the object has been marked with @rule; otherwise None.
    """
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
