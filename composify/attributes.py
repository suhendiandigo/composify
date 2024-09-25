"""Default attributes implemented by Composify.

Attributes allows augmentation to the dependency graph resolution
by exact matching.


Example:
    from composify import Composify, rule, collect_rules
    from composify.attributes import Name

    class A(int):
        pass

    @rule
    def a_value_1() -> Annotated[A, Name("main")]:
        return 1

    @rule
    def a_value_2() -> Annotated[A, Name("other")]:
        return 2

    composify = Composify(rules=collect_rules())

    result = composify.get_or_create(Annotated[A, Name("other")])
    print(result)
    #> 2
    result = composify.get_or_create(Annotated[A, Name("main")])
    print(result)
    #> 1
"""

from ._attributes import Name, ProvidedBy

__all__ = ("Name", "ProvidedBy")
