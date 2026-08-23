"""Job Shop — high-mix, low-volume custom parts manufacturing.

Scenario: A custom fabrication shop with general-purpose machines:
- CNC lathe, CNC mill, drill press, surface grinder
- Each order is a unique part requiring a specific routing
- Operators with skill levels restrict scheduling
- Setup times between different part types

This demonstrates APS's ability to handle:
- Alternative machines for the same operation
- Operator certification constraints
- Sequence-dependent setup times
"""

from __future__ import annotations

from aps.unified._schema import PlanningModel
from aps.unified.scenarios._generator import ScenarioGenerator

SCENARIO_ID = "job_shop"
SCENARIO_NAME = "Job Shop Manufacturing"
SCENARIO_DESCRIPTION = (
    "High-mix, low-volume custom parts. 4 machine types (lathe, mill, drill, grinder), "
    "2 of each, 3 senior operators, 5 unique customer orders with different routings. "
    "Setup times between jobs, operator skill constraints."
)


def generate(*, seed: int = 0) -> PlanningModel:
    """Generate the Job Shop scenario.

    Args:
        seed: Random seed for variant generation.

    Returns:
        A PlanningModel for the scenario.
    """
    gen = ScenarioGenerator(seed=seed)
    return gen.generate(
        palette="metalworking",
        num_machine_types=3,
        machines_per_type=2,
        bom_depth=2,
        num_raw_materials=4,
        num_final_products=2,
        rules_per_stage=2,     # 2 rules per stage for alternative paths
        num_operators=3,       # more operators
        num_orders=3,
        order_qty_range=(3, 10),
        duration_per_unit_range=(30, 180),
        duration_batch_range=(10, 30),
        batch_min=1,
        batch_max=6,
        horizon_days=45,
        setup_times=True,
    )
