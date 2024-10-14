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
import itertools
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field
from functools import partial, reduce
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

from composify._helper import (
    GenericInfo,
    TypeInfo,
    ensure_type_annotation,
    get_type_info,
    resolve_type_name,
)
from composify._registry import (
    DefaultEntriesCollator,
    DefaultEntriesFilterer,
    EntriesCollator,
    EntriesFilterer,
    Entry,
    FilteringContext,
    Key,
    MemoizedTypeResolver,
    TypedRegistry,
)
from composify.errors import (
    MissingParameterTypeAnnotation,
    MissingReturnTypeAnnotation,
)
from composify.metadata import AttributeSet, collect_attributes
from composify.metadata.qualifiers import BaseQualifierMetadata
from composify.types import AnnotatedType
from composify.variance import INVARIANT

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
    generic: GenericInfo | None

    @property
    def key(self) -> Key:
        return self.output_type

    @property
    def name(self) -> str:
        return self.canonical_name

    @property
    def is_generic(self):
        return self.generic is not None


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
        generic=return_type_info.generic,
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


class AsyncRuleNotSupportedError(RuleError):
    def __init__(self, rule: ConstructRule) -> None:
        self.rule = rule
        super().__init__(f"Async rule is not supported for registry: {rule!r}.")


class GenericRuleNotSupportedError(RuleError):
    def __init__(self, rule: ConstructRule) -> None:
        self.rule = rule
        super().__init__(f"Generic rule is supported for registry: {rule!r}.")


class RuleRegistry:
    __slots__ = ("_rules", "_type_resolver", "_supports_async")

    _rules: TypedRegistry[ConstructRule]

    def __init__(
        self,
        rules: Iterable[ConstructRule] | None = None,
        *,
        entries_filterer: EntriesFilterer | None = None,
        entries_collator: EntriesCollator | None = None,
        type_resolver: MemoizedTypeResolver | None = None,
        supports_async: bool = True,
    ) -> None:
        self._type_resolver = type_resolver or MemoizedTypeResolver()
        self._rules = TypedRegistry(
            rules,
            entries_filterer=entries_filterer,
            entries_collator=entries_collator,
            type_resolver=self._type_resolver,
        )
        self._supports_async = supports_async

    @property
    def supports_async(self) -> bool:
        return self._supports_async

    def _compare_entries(
        self, entry: ConstructRule, other: ConstructRule
    ) -> bool:
        return entry == other

    def register_rule(self, rule: ConstructRule) -> None:
        if rule.is_async and not self.supports_async:
            raise AsyncRuleNotSupportedError(rule)
        if rule.is_generic:
            raise GenericRuleNotSupportedError(rule)
        self._rules.add_entry(rule)

    def register_rules(self, rules: Iterable[ConstructRule]) -> None:
        for rule in rules:
            self.register_rule(rule)

    def get(self, target: AnnotatedType[T]) -> Iterable[ConstructRule[T]]:
        return self._rules.get(target)


@dataclass(frozen=True)
class GenericRuleEntry(Entry, Generic[T]):
    entry_name: str
    parameter_type: type
    registry: TypedRegistry["GenericRuleEntry"] | None = field(compare=False)
    rule: ConstructRule | None
    attributes: AttributeSet
    priority: int = field(compare=False)

    @property
    def key(self) -> Key:
        return self.parameter_type

    @property
    def name(self) -> str:
        return self.entry_name


class _GenericRuleRegistry:
    _rules: TypedRegistry[GenericRuleEntry]

    def __init__(
        self,
        rules: Iterable[ConstructRule] | None = None,
        *,
        entries_filterer: EntriesFilterer | None = None,
        entries_collator: EntriesCollator | None = None,
        type_resolver: MemoizedTypeResolver | None = None,
    ):
        self._type_resolver = type_resolver or MemoizedTypeResolver()
        self._entries_filterer = entries_filterer or DefaultEntriesFilterer()
        self._entries_collator = entries_collator or DefaultEntriesCollator()
        self._rules = self._create_registry()
        if rules:
            for rule in rules:
                self.add_rule(rule)

    def _create_registry(self) -> TypedRegistry[GenericRuleEntry]:
        return TypedRegistry(
            None,
            entries_filterer=self._entries_filterer,
            entries_collator=self._entries_collator,
            type_resolver=self._type_resolver,
        )

    def add_rule(self, rule: ConstructRule) -> None:
        if not rule.is_generic:
            raise ValueError(f"{rule!r} is not a generic rule")

        args = (rule.output_type, *rule.generic.args)
        current_rules = {self._rules}
        next_rules = []
        last_idx = len(args) - 1
        for i, arg in enumerate(args):
            if i == last_idx:
                entry = GenericRuleEntry(
                    entry_name=f"generic_{rule.output_type.__module__}.{rule.output_type.__name__}_arg_{i}_{arg.__module__}.{arg.__name__}",
                    parameter_type=arg,
                    registry=None,
                    rule=rule,
                    attributes=collect_attributes(arg),
                    priority=rule.priority,
                )
                for rules_ in current_rules:
                    rules_.add_entry(entry)
            else:
                context = FilteringContext.from_type(arg)
                for rules_ in current_rules:
                    entries = self._entries_filterer.filter_entries(
                        rules_.get(arg, INVARIANT), context
                    )
                    if entries:
                        next_rules.extend(entry.registry for entry in entries)
                    else:
                        entry = GenericRuleEntry(
                            entry_name=f"generic_{arg.__module__}.{arg.__name__}"
                            if i == 0
                            else f"generic_{rule.output_type.__module__}.{rule.output_type.__name__}_arg_{i}_{arg.__module__}.{arg.__name__}",
                            parameter_type=arg,
                            registry=self._create_registry(),
                            rule=None,
                            attributes=collect_attributes(arg),
                            priority=rule.priority,
                        )
                        next_rules.append(entry.registry)
                        rules_.add_entry(entry)
            current_rules = next_rules
            next_rules = []

    def get(self, target: TypeInfo) -> Iterable[ConstructRule[T]]:
        args = (target.inner_type, *target.generic.args)
        current_rules = [self._rules]
        next_rules = []
        last_idx = len(args) - 1
        for i, arg in enumerate(args):
            context = FilteringContext.from_type(arg)
            entries = tuple(
                itertools.chain.from_iterable(
                    self._entries_filterer.filter_entries(
                        r.get(arg, INVARIANT), context
                    )
                    for r in current_rules
                )
            )
            if not entries:
                break
            if i == last_idx:
                for entry in entries:
                    if entry.rule is not None:
                        yield entry.rule
            else:
                for entry in entries:
                    next_rules.append(entry.registry)
            current_rules = next_rules
            next_rules = []


def partition(iterable, key):
    return reduce(lambda x, y: x[not key(y)].append(y) or x, iterable, ([], []))


class SupportsGenericRuleRegistry(RuleRegistry):
    __slots__ = ("_generic_rules",)

    _rules: TypedRegistry[ConstructRule]
    _generic_rules: _GenericRuleRegistry

    def __init__(
        self,
        rules: Iterable[ConstructRule] | None = None,
        *,
        entries_filterer: EntriesFilterer | None = None,
        entries_collator: EntriesCollator | None = None,
        type_resolver: MemoizedTypeResolver | None = None,
        supports_async: bool = True,
    ) -> None:
        self._type_resolver = type_resolver or MemoizedTypeResolver()
        generic_rules, non_generic_rules = partition(
            rules, key=lambda x: x.is_generic
        )
        super().__init__(
            non_generic_rules,
            entries_filterer=entries_filterer,
            entries_collator=entries_collator,
            type_resolver=self._type_resolver,
            supports_async=supports_async,
        )
        self._generic_rules = _GenericRuleRegistry(
            generic_rules,
            entries_filterer=entries_filterer,
            entries_collator=entries_collator,
            type_resolver=self._type_resolver,
        )

    def register_rule(self, rule: ConstructRule) -> None:
        if rule.is_async and not self.supports_async:
            raise AsyncRuleNotSupportedError(rule)
        if rule.is_generic:
            self._generic_rules.add_rule(rule)
        else:
            self._rules.add_entry(rule)

    def get(self, target: AnnotatedType[T]) -> Iterable[ConstructRule[T]]:
        type_info = get_type_info(target)
        if type_info.is_generic:
            return self._generic_rules.get(type_info)
        return self._rules.get(target)
