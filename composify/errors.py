"""Module containing errors classes."""

from collections.abc import Iterable, Sequence
from typing import Any, TypeAlias


class ResolverError(Exception):
    """Base class for all resolution errors."""

    pass


class InvalidResolutionModeError(ResolverError):
    """Raised for invalid resolution mode."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        super().__init__(
            f"Invalid resolution mode {mode!r}",
        )


class MultipleResolutionError(ResolverError):
    """Raised when there are multiple resolutions for a type."""

    def __init__(self, type_: type, resolutions: Any) -> None:
        self.type_ = type_
        self.resolutions = resolutions
        super().__init__(
            f"Multiple resolution found for {type_!r}",
        )


class NoResolutionError(ResolverError):
    """Raised when there is no resolution for a type."""

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
    """Raised when an error ocurred in a blueprint resolution."""

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
    """Raised when blueprint resolution returns no result. This error contains
    all exceptions that ocurred while resolving.
    """

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
        """Checks if any exception raised was of a specific type.

        Args:
            exc_type (type[ResolverError]): The exc type to find.

        Returns:
            bool: True if an exception of type exc_type exists; otherwise False.
        """
        for error in self.errors:
            if isinstance(error, exc_type):
                return True
        return False


class TracedTypeConstructionResolutionError(TypeConstructionResolutionError):
    """Raised when an error ocurred in a blueprint resolution containing the
    tracing of resolution.
    """

    def __init__(self, type_: type, traces: Traces, msg: str) -> None:
        super().__init__(type_, msg)
        self.traces = traces


class NoConstructorError(TracedTypeConstructionResolutionError):
    """Raised when there is no available constructor for a specific type."""

    def __init__(self, type_: type, traces: Traces) -> None:
        super().__init__(
            type_, traces, f"Unable to find constructor for {type_!r}"
        )


class CyclicDependencyError(TracedTypeConstructionResolutionError):
    """Raised when a cyclic dependency occurred in the dependency graph."""

    def __init__(self, type_: type, traces: Traces) -> None:
        super().__init__(
            type_, traces, f"Cyclic dependency found for {type_!r}"
        )


class MultipleDependencyResolutionError(TracedTypeConstructionResolutionError):
    """Raised when a dependency contains multiple resolutions in UNIQUE resolution mode."""

    def __init__(
        self, type_: type, solutions: Sequence[str], traces: Traces
    ) -> None:
        self.solutions = solutions
        super().__init__(
            type_,
            traces,
            f"Multiple dependency resolutions found for {type_!r}: {', '.join(solutions)}",
        )


class ContainerError(Exception):
    """Base classes for all container related errors."""

    pass


class InstanceRetrievalError(ContainerError):
    """Raised for instance retrieval errors."""

    pass


class InstanceNotFoundError(InstanceRetrievalError):
    """Raised when an instance is not found."""

    pass


class InstanceOfTypeNotFoundError(InstanceNotFoundError):
    """Raised when an instance of a specific type is not found."""

    def __init__(self, to_find: Any):
        self.to_find = to_find
        super().__init__(f"Instance of type {to_find} not found")


class InstanceOfNameNotFoundError(InstanceNotFoundError):
    """Raised when an instance with a specific name is not found."""

    def __init__(self, to_find: Any):
        self.to_find = to_find
        super().__init__(f"Instance of name {to_find!r} not found")


class AmbiguousInstanceError(InstanceRetrievalError):
    """Raised when instances to retrieve are ambiguous."""

    def __init__(self, to_find: Any, candidates: Sequence[Any]):
        self.to_find = to_find
        self.candidates = candidates
        super().__init__(
            f"Ambiguous components found for {to_find}: {candidates}"
        )


class InstanceAdditionError(ContainerError):
    """Raised for instances collation errors."""

    pass


class ConflictingInstanceNameError(InstanceAdditionError):
    """Raised when trying to collate multiple instances with the exact name."""

    def __init__(self, name: str, to_add: Any, existing: Any):
        self.name = name
        self.to_add = to_add
        self.existing = existing
        super().__init__(
            f"New instance '{to_add}' with name {name!r} is conflicting with currently existing instance '{existing}'"
        )


class MultiplePrimaryInstanceError(InstanceAdditionError):
    """Raised when trying to collate multiple primary instances."""

    def __init__(self, to_add: Any, existing: Any):
        self.to_add = to_add
        self.existing = existing
        super().__init__(
            f"New primary '{to_add}' is conflicting with existing primary '{existing}'"
        )


class RegistryError(Exception):
    """Base class for all registry related errors."""

    pass


class DuplicatedEntryError(RegistryError):
    """Raised when duplicate entry are collated together."""

    def __init__(self, to_add: Any, existing: Any) -> None:
        self.to_add = to_add
        self.existing = existing
        super().__init__(
            f"Entry {to_add!r} conflict with existing entry {existing!r}"
        )


class InvalidTypeAnnotation(TypeError):
    """Raised for invalid type annotation."""

    pass


class MissingReturnTypeAnnotation(InvalidTypeAnnotation):
    """Raised when type annotation for a return value is missing."""

    pass


class MissingParameterTypeAnnotation(InvalidTypeAnnotation):
    """Raised when type annotation for a parameter is missing."""

    pass


class BuilderError(Exception):
    """Base class for all Builder related errors."""

    pass


class AsyncBlueprintError(BuilderError):
    """Raised when trying to create an async blueprint using sync Builder."""

    pass


class NonOptionalBuilderMismatchError(BuilderError):
    """Raised when a builder resulted in None value for non optional blueprint."""

    pass


class NoValueError(BuilderError):
    """Raised when a series of optional blueprints do not return any value."""

    pass
