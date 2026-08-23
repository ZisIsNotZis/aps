"""Assembly Line — progressive assembly of complex products.

Scenario: A multi-station assembly line producing electric scooters:
- Frame preparation station
- Motor & drivetrain assembly
- Electronics & wiring station
- Final assembly & testing

Each station processes one unit at a time in sequence.
Multiple scooter variants (standard, premium) share the line.
Demonstrates line balancing and multi-variant production scheduling.
"""

from __future__ import annotations

from aps.unified._schema import PlanningModel
from aps.unified.scenarios._generator import ScenarioGenerator

SCENARIO_ID = "assembly_line"
SCENARIO_NAME = "Assembly Line Production"
SCENARIO_DESCRIPTION = (
    "Progressive assembly of electric scooters across 4 stations. "
    "2 product variants (standard, premium), 4 assembly stations in sequence, "
    "2 operators, shared components between variants. "
    "Demonstrates line balancing and multi-variant scheduling."
)


def generate(*, seed: int = 0) -> PlanningModel:
    """Generate the Assembly Line scenario.

    Args:
        seed: Random seed for variant generation.

    Returns:
        A PlanningModel for the scenario.
    """
    gen = ScenarioGenerator(seed=seed)
    return gen.generate(
        palette="assembly",
        num_machine_types=3,
        machines_per_type=2,
        bom_depth=2,
        num_raw_materials=4,
        num_final_products=2,
        rules_per_stage=1,
        num_operators=2,
        num_orders=3,
        order_qty_range=(5, 15),
        duration_per_unit_range=(30, 120),
        duration_batch_range=(0, 10),
        batch_min=1,
        batch_max=10,
        horizon_days=30,
        setup_times=True,
    )
