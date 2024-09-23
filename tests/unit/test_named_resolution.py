from dataclasses import dataclass
from typing import Annotated

import pytest

from composify.metadata import Name
from composify.rules import collect_rules, rule
from tests.utils import blueprint, compare_blueprints, create_rule_resolver


@dataclass(frozen=True)
class A:
    value: int


@rule
def create_a() -> A:
    return A(100)


rules_1 = collect_rules()


@rule
def create_special() -> Annotated[A, Name("special")]:
    return A(10)


rules_2 = collect_rules()


@pytest.mark.asyncio_cooperative
async def test_no_named():
    resolver = create_rule_resolver(*rules_1)

    compare_blueprints(
        resolver.resolve(Annotated[A, Name("special")]), [blueprint(create_a)]
    )


@pytest.mark.asyncio_cooperative
async def test_multiple_with_named():
    resolver = create_rule_resolver(*rules_2)

    compare_blueprints(
        resolver.resolve(Annotated[A, Name("special")]),
        [
            blueprint(create_special),
        ],
    )

    compare_blueprints(
        resolver.resolve(A),
        [
            blueprint(create_a),
            blueprint(create_special),
        ],
    )
