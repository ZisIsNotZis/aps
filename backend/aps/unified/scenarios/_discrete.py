"""Discrete manufacturing scenario — one machine, one rule, one order.

Simplest scenario: steel_kg → component_each on a CNC machine.
"""

from __future__ import annotations

from datetime import UTC, datetime

from aps.unified._schema import (
    Entity,
    Objective,
    Order,
    PlanningModel,
    Rule,
    Selector,
)

SCENARIO_ID = "discrete_manufacturing"
SCENARIO_NAME = "Discrete Manufacturing"
SCENARIO_DESCRIPTION = "One machine, one rule, one order — simple CNC machining."


def generate(*, seed: int = 0) -> PlanningModel:
    """Generate a discrete manufacturing scenario.

    Args:
        seed: Random seed for variant generation (default 0 = deterministic).

    Returns:
        A PlanningModel for the discrete manufacturing scenario.
    """
    _ = seed  # unused for now, deterministic
    return PlanningModel(
        entities=[
            Entity(fields={"type": "steel_kg", "location": "plant_a"}, count=5),
            Entity(fields={"type": "cnc_machine", "state": "idle", "location": "plant_a"}),
        ],
        rules=[
            Rule(
                rule_id="make_component",
                consume={"steel": Selector(conditions={"type": "steel_kg"})},
                consume_batch={"machine": Selector(conditions={"type": "cnc_machine", "state": "idle"})},
                produce={"component": Selector(conditions={"type": "component_each"})},
                produce_batch={"machine": Selector(conditions={"type": "cnc_machine", "state": "idle"})},
                duration_s=60.0,
                batch_min=1,
                batch_max=10,
            ),
        ],
        orders=[
            Order(
                order_id="ORD-1",
                consume={"component": Selector(conditions={"type": "component_each"}, num=5)},
                deadline=datetime(2026, 8, 15, tzinfo=UTC),
            ),
        ],
        objective=Objective(expression="$money_cent_remaining"),
        planning_start=datetime(2026, 7, 24, tzinfo=UTC),
        planning_horizon_s=86400 * 30,
    )
