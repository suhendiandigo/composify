from typing import Any, Iterable, TypeAlias


class ContainerError(Exception):
    pass


class InstanceError(ContainerError):
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


class AmbiguousInstanceError(InstanceError):
    def __init__(self, to_find: Any, candidates: tuple[Any, ...]):
        self.to_find = to_find
        self.candidates = candidates
        super().__init__(
            f"Ambiguous components found for {to_find}: {candidates}"
        )


class ConflictingInstanceNameError(InstanceError):
    def __init__(self, name: str, to_add: Any, existing: Any):
        self.name = name
        self.to_add = to_add
        self.existing = existing
        super().__init__(
            f"New instance '{to_add}' with name {name!r} is conflicting with currently existing instance '{existing}'"
        )


class MultiplePrimaryInstanceError(InstanceError):
    def __init__(self, to_add: Any, existing: Any):
        self.to_add = to_add
        self.existing = existing
        super().__init__(
            f"New primary '{to_add}' is conflicting with existing primary '{existing}'"
        )


class ResolverError(Exception):
    pass


class TypeConstructionResolutionError(ResolverError):

    def __init__(self, type_: type, msg: str) -> None:
        super().__init__(msg)
        self.type_ = type_


Trace: TypeAlias = tuple[str, str, type]
Traces: TypeAlias = tuple[Trace, ...]


class TracedTypeConstructionResolutionError(TypeConstructionResolutionError):

    def __init__(self, type_: type, traces: Traces, msg: str) -> None:
        super().__init__(type_, msg)
        self.traces = traces


class NoConstructPlanError(TracedTypeConstructionResolutionError):
    def __init__(self, type_: type, traces: Traces) -> None:
        super().__init__(
            type_, traces, f"Unable to find construction plan for {type_!r}"
        )


class CyclicDependencyError(TracedTypeConstructionResolutionError):
    def __init__(self, type_: type, traces: Traces) -> None:
        super().__init__(
            type_, traces, f"Cyclic dependency found for {type_!r}"
        )


class FailedToResolveError(TracedTypeConstructionResolutionError):
    def __init__(
        self,
        type_: type,
        traces: Traces,
        errors: Iterable[TracedTypeConstructionResolutionError],
    ) -> None:
        self.errors = errors
        super().__init__(
            type_,
            traces,
            f"Failed to resolve for {type_!r}",
        )
