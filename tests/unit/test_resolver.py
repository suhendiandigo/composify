import pytest

from composify.errors import (
    MultipleDependencyResolutionError,
    ResolutionFailureError,
)
from composify.provider import ContainerInstanceProvider
from composify.resolutions import UNIQUE
from tests.example_complex_rules import (
    Param,
    Result,
    create_direct_result,
    create_result,
    default_param,
    infer_param_1,
    infer_param_2,
    rules_1,
    rules_2,
)
from tests.utils import (
    blueprint,
    create_resolver,
    create_rule_provider,
    create_rule_resolver,
    instance,
)


def test_comparison():
    resolver = create_resolver(
        create_rule_provider(*rules_1),
    )
    plans = list(resolver.resolve(Param))
    assert plans[0] == blueprint(default_param)
    assert plans[0] != blueprint(create_result)


def test_plan_ordering(container, compare_blueprints):
    resolver = create_resolver(
        ContainerInstanceProvider(container),
        create_rule_provider(*rules_1),
    )
    _value = Param(5)
    container.add(_value)
    compare_blueprints(
        resolver.resolve(Result),
        [
            blueprint(create_direct_result, param=instance(Param, 0)),
            blueprint(create_direct_result, param=blueprint(default_param)),
            blueprint(
                create_result,
                param1=blueprint(infer_param_1, param=instance(Param, 0)),
                param2=blueprint(infer_param_2, param=instance(Param, 0)),
            ),
            blueprint(
                create_result,
                param1=blueprint(infer_param_1, param=instance(Param, 0)),
                param2=blueprint(infer_param_2, param=blueprint(default_param)),
            ),
            blueprint(
                create_result,
                param1=blueprint(infer_param_1, param=blueprint(default_param)),
                param2=blueprint(infer_param_2, param=instance(Param, 0)),
            ),
            blueprint(
                create_result,
                param1=blueprint(infer_param_1, param=blueprint(default_param)),
                param2=blueprint(infer_param_2, param=blueprint(default_param)),
            ),
        ],
    )


def test_rule_resolver(compare_blueprints):
    resolver = create_rule_resolver(*rules_1)

    compare_blueprints(
        resolver.resolve(Result),
        [
            blueprint(create_direct_result, param=blueprint(default_param)),
            blueprint(
                create_result,
                param1=blueprint(infer_param_1, param=blueprint(default_param)),
                param2=blueprint(infer_param_2, param=blueprint(default_param)),
            ),
        ],
    )


def test_container_resolver(container, container_resolver, compare_blueprints):
    _value = Param(5)
    container.add(_value)

    compare_blueprints(
        container_resolver.resolve(Param),
        [
            instance(Param, 0),
        ],
    )


def test_unique_resolver_error():
    resolver = create_rule_resolver(*rules_2, default_resolution=UNIQUE)

    with pytest.raises(ResolutionFailureError) as exc:
        (resolver.resolve(Result),)
    assert exc.value.contains(MultipleDependencyResolutionError)


def test_unique_resolver(compare_blueprints):
    resolver = create_rule_resolver(*rules_1, default_resolution=UNIQUE)

    with pytest.raises(ResolutionFailureError) as exc:
        (resolver.resolve(Result),)
    assert exc.value.contains(MultipleDependencyResolutionError)
    # compare_blueprints(
    #     resolver.resolve(Result),
    #     [
    #         blueprint(create_direct_result, param=blueprint(default_param)),
    #         blueprint(
    #             create_result,
    #             param1=blueprint(infer_param_1, param=blueprint(default_param)),
    #             param2=blueprint(infer_param_2, param=blueprint(default_param)),
    #         ),
    #     ],
    # )
