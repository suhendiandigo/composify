from fixture.example_complex_rules import (
    Param,
    Result,
    create_result,
    default_param,
    infer_param_1,
    infer_param_2,
    rules,
)

from declarative_app.provider import ContainerInstanceProvider
from tests.utils import (
    blueprint,
    compare_blueprints,
    create_resolver,
    create_rule_provider,
    create_rule_resolver,
    static,
)


def test_comparison():
    resolver = create_resolver(
        create_rule_provider(*rules),
    )
    plans = list(resolver.resolve(Param))
    assert plans[0] == blueprint(default_param)
    assert plans[0] != blueprint(create_result)


def test_plan_ordering(container):
    resolver = create_resolver(
        ContainerInstanceProvider(container),
        create_rule_provider(*rules),
    )
    _value = Param(5)
    container.add(_value)
    compare_blueprints(
        resolver.resolve(Result),
        [
            blueprint(
                create_result,
                param1=blueprint(infer_param_1, param=static(_value)),
                param2=blueprint(infer_param_2, param=static(_value)),
            ),
            blueprint(
                create_result,
                param1=blueprint(infer_param_1, param=static(_value)),
                param2=blueprint(
                    infer_param_2, param=blueprint(default_param)
                ),
            ),
            blueprint(
                create_result,
                param1=blueprint(
                    infer_param_1, param=blueprint(default_param)
                ),
                param2=blueprint(infer_param_2, param=static(_value)),
            ),
            blueprint(
                create_result,
                param1=blueprint(
                    infer_param_1, param=blueprint(default_param)
                ),
                param2=blueprint(
                    infer_param_2, param=blueprint(default_param)
                ),
            ),
        ],
    )


def test_rule_resolver():
    resolver = create_rule_resolver(*rules)

    compare_blueprints(
        resolver.resolve(Result),
        [
            blueprint(
                create_result,
                param1=blueprint(
                    infer_param_1, param=blueprint(default_param)
                ),
                param2=blueprint(
                    infer_param_2, param=blueprint(default_param)
                ),
            ),
        ],
    )


def test_container_resolver(container, container_resolver):
    _value = Param(5)
    container.add(_value)

    compare_blueprints(
        container_resolver.resolve(Param),
        [
            static(_value),
        ],
    )
