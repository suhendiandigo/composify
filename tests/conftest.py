from collections.abc import Iterable
from itertools import zip_longest

from pytest import fixture

from composify.blueprint import Blueprint, BlueprintResolver
from composify.container import Container
from composify.provider import ContainerInstanceProvider
from tests.utils import find_difference


@fixture(scope="function")
def container() -> Container:
    return Container()


@fixture(scope="function")
def container_resolver(container) -> BlueprintResolver:
    return BlueprintResolver([ContainerInstanceProvider(container)])


def _select_bp(bp: Blueprint, path: tuple[str, ...]) -> Blueprint:
    if not path:
        return bp
    top, rest = path[0], path[1:]
    return _select_bp(
        next(iter(filter(lambda x: x[0] == top, bp.dependencies)))[1], rest
    )


_COMPARED_ATTRS = ("constructor", "is_async", "dependencies")


def pytest_assertrepr_compare(op, left, right):
    if (
        isinstance(left, Blueprint)
        and isinstance(right, Blueprint)
        and op == "=="
    ):
        diff_path = find_difference(left, right)
        if diff_path is not None:
            result = ["blueprint instances:"]
            path_str = "->".join(("root",) + diff_path)
            result.append(f"   path: {path_str}")
            left_bp = _select_bp(left, diff_path)
            right_bp = _select_bp(right, diff_path)
            for attr in _COMPARED_ATTRS:
                left_val = getattr(left_bp, attr)
                right_val = getattr(right_bp, attr)
                if not left_val == right_val:
                    result.append(f"   {attr}: {left_val} != {right_val}")
            return result


def _compare_blueprints(
    plans: Iterable[Blueprint], expected_plans: Iterable[Blueprint]
):
    plans = list(plans)
    expected_plans = list(expected_plans)
    assert len(plans) == len(
        expected_plans
    ), f"different plan len {len(plans)} != {len(expected_plans)}"
    for index, (plan, expected) in enumerate(
        zip_longest(plans, expected_plans)
    ):
        assert plan == expected, f"case {index}"


@fixture
def compare_blueprints():
    return _compare_blueprints
