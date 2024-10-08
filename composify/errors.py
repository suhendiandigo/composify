from collections.abc import Iterable, Sequence
from typing import Any, TypeAlias


class ResolverError(Exception):
    pass


class InvalidResolutionModeError(ResolverError):
    def __init__(self, mode: str) -> None:
        self.mode = mode
        super().__init__(
            f"Invalid resolution mode {mode!r}",
        )


class MultipleResolutionError(ResolverError):
    def __init__(self, type_: type, resolutions: Any) -> None:
        self.type_ = type_
        self.resolutions = resolutions
        super().__init__(
            f"Multiple resolution found for {type_!r}",
        )


class NoResolutionError(ResolverError):
    def __init__(
        self,
        type_: type,
    ) -> None:
        self.type_ = type_
        super().__init__(
            type_,
            f"No resolution found for {type_!r}",
        )


class TypeConstructionResolutionError(ResolverError):
    def __init__(self, type_: type, msg: str) -> None:
        super().__init__(msg)
        self.type_ = type_


Trace: TypeAlias = tuple[str, str, type]
Traces: TypeAlias = tuple[Trace, ...]


def _format_trace(trace: Trace) -> str:
    return (
        f"({trace[1]}: {trace[0]} -> {trace[2].__module__}.{trace[2].__name__})"
    )


def _format_traces(traces: Traces) -> str:
    return "->".join(_format_trace(trace) for trace in traces)


class ResolutionFailureError(TypeConstructionResolutionError):
    def __init__(
        self, type_: type, traces: Traces, errors: Iterable[ResolverError]
    ) -> None:
        error_strings = tuple(
            f"- {_format_traces(error.traces)}: {error}"
            if isinstance(error, TracedTypeConstructionResolutionError)
            else f"- {error}"
            for error in errors
        )
        error_string = "\n".join(error_strings)
        super().__init__(
            type_, f"Failed to resolve for type {type_}\n{error_string}"
        )
        self.traces = traces
        self.errors = errors

    def contains(self, exc_type: type[ResolverError]) -> bool:
        for error in self.errors:
            if isinstance(error, exc_type):
                return True
        return False


class TracedTypeConstructionResolutionError(TypeConstructionResolutionError):
    def __init__(self, type_: type, traces: Traces, msg: str) -> None:
        super().__init__(type_, msg)
        self.traces = traces


class NoConstructorError(TracedTypeConstructionResolutionError):
    def __init__(self, type_: type, traces: Traces) -> None:
        super().__init__(
            type_, traces, f"Unable to find constructor for {type_!r}"
        )


class CyclicDependencyError(TracedTypeConstructionResolutionError):
    def __init__(self, type_: type, traces: Traces) -> None:
        super().__init__(
            type_, traces, f"Cyclic dependency found for {type_!r}"
        )


class ContainerError(Exception):
    pass


class InstanceNotFoundError(ContainerError):
    pass


class InstanceOfTypeNotFoundError(InstanceNotFoundError):
    def __init__(self, to_find: Any):
        self.to_find = to_find
        super().__init__(f"Instance of type {to_find} not found")


class InstanceOfNameNotFoundError(InstanceNotFoundError):
    def __init__(self, to_find: Any):
        self.to_find = to_find
        super().__init__(f"Instance of name {to_find!r} not found")


class InstanceRetrievalError(ContainerError):
    pass


class AmbiguousInstanceError(InstanceRetrievalError):
    def __init__(self, to_find: Any, candidates: Sequence[Any]):
        self.to_find = to_find
        self.candidates = candidates
        super().__init__(
            f"Ambiguous components found for {to_find}: {candidates}"
        )


class InstanceAdditionError(ContainerError):
    pass


class ConflictingInstanceNameError(InstanceAdditionError):
    def __init__(self, name: str, to_add: Any, existing: Any):
        self.name = name
        self.to_add = to_add
        self.existing = existing
        super().__init__(
            f"New instance '{to_add}' with name {name!r} is conflicting with currently existing instance '{existing}'"
        )


class MultiplePrimaryInstanceError(InstanceAdditionError):
    def __init__(self, to_add: Any, existing: Any):
        self.to_add = to_add
        self.existing = existing
        super().__init__(
            f"New primary '{to_add}' is conflicting with existing primary '{existing}'"
        )


class RegistryError(Exception):
    pass


class UnsupportedTypeError(RegistryError):
    def __init__(self, type_: type) -> None:
        super().__init__(f"Type of {type_} is unsupported")


class DuplicatedEntryError(RegistryError):
    def __init__(self, to_add: Any, existing: Any) -> None:
        self.to_add = to_add
        self.existing = existing
        super().__init__(
            f"Entry {to_add!r} conflict with existing entry {existing!r}"
        )


class InvalidTypeAnnotation(TypeError):
    pass


class MissingReturnTypeAnnotation(InvalidTypeAnnotation):
    pass


class MissingParameterTypeAnnotation(InvalidTypeAnnotation):
    pass


class BuilderError(Exception):
    pass


class AsyncBlueprintError(Exception):
    pass
