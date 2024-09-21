import asyncio
import inspect
from dataclasses import dataclass
from types import FrameType, ModuleType
from typing import (
    Any,
    Awaitable,
    Callable,
    Iterable,
    Mapping,
    ParamSpec,
    Type,
    TypeVar,
    get_type_hints,
)

from typing_extensions import TypeAlias

__all__ = ["rule", "get_rule_metadata"]


T = TypeVar("T")
P = ParamSpec("P")


SyncRuleFunctionType: TypeAlias = Callable[P, T]
AsyncRuleFunctionType: TypeAlias = Callable[P, Awaitable[T]]
RuleFunctionType: TypeAlias = SyncRuleFunctionType | AsyncRuleFunctionType

F = TypeVar("F", bound=RuleFunctionType)
RULE_ATTR = "__rule__"


@dataclass(frozen=True)
class ConstructRule:
    function: RuleFunctionType
    is_async: bool
    cannonical_name: str
    output_type: Type
    parameter_types: Mapping[str, Type]

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)


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
    type_hints = get_type_hints(func)
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


def get_rule_metadata(f: Any) -> ConstructRule | None:
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
