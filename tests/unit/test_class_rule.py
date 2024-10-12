from composify.rules import as_rule, rule


def test_empty_class():
    @rule
    class OurComponent:
        pass

    rule_ = as_rule(OurComponent)
    assert not rule_.parameter_types


def test_class_param():
    @rule
    class OurComponent:
        def __init__(self, param1: int, param2: str) -> None:
            pass

    rule_ = as_rule(OurComponent)
    assert len(rule_.parameter_types) == 2
    assert rule_.parameter_types[0][1] is int
    assert rule_.parameter_types[1][1] is str
