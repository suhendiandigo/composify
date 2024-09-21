from typing import Any


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
