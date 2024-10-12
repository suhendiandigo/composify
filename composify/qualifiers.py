"""This module contains qualifiers metadata.

Qualifiers allows augmentation to the dependency graph resolution.

Example:
    from composify import Composify, rule, collect_rules
    from composify.qualifiers import Exhaustive

    class A(int):
        pass

    @rule
    def a_value_1() -> A:
        return 1

    @rule
    def a_value_2() -> A:
        return 2

    composify = Composify(rules=collect_rules())

    results = composify.get_or_create_all(A)
    print(len(results))
    #> 1
    print(results[0])
    #> 1

"""

from composify._qualifiers import (
    DisallowSubclass,
    Exhaustive,
    Resolution,
    SelectFirst,
)

__all__ = (
    "DisallowSubclass",
    "Resolution",
    "Exhaustive",
    "SelectFirst",
)
