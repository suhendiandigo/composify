from typing import Any, TypeAlias


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
    def __init__(self, to_find: Any, candidates: tuple[Any]):
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
    pass


Trace: TypeAlias = tuple[str, str, type]
Traces: TypeAlias = tuple[Trace, ...]


class FailedToResolveError(TypeConstructionResolutionError):
    def __init__(self, type_: type, traces: Traces) -> None:
        self.type_ = type_
        self.traces = traces
        super().__init__(f"Failed to resolve for {self.type_!r}")


class NoConstructPlanError(TypeConstructionResolutionError):
    def __init__(self, type_: type, traces: Traces) -> None:
        self.type_ = type_
        self.traces = traces
        super().__init__(
            f"Unable to find construction plan for {self.type_!r}"
        )


class CyclicDependencyError(TypeConstructionResolutionError):
    def __init__(self, type_: type, traces: Traces) -> None:
        self.type_ = type_
        self.traces = traces
        super().__init__(f"Cyclic dependency found for {self.type_!r}")
