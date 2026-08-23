"""Furniture Manufacturing — multi-product woodworking factory.

Scenario: A custom furniture factory producing:
- Oak cabinets, walnut desks, plywood shelves
- Multiple production stages: cutting, edging, drilling, assembly, finishing
- Parallel production lines for different product families
- Finishing/painting station as a shared bottleneck
- Large raw material inventory with multiple wood species

Demonstrates multi-product family scheduling with shared bottleneck resources.
"""

from __future__ import annotations

from aps.unified._schema import PlanningModel
from aps.unified.scenarios._generator import ScenarioGenerator

SCENARIO_ID = "furniture_manufacturing"
SCENARIO_NAME = "Furniture Manufacturing"
SCENARIO_DESCRIPTION = (
    "Multi-product woodworking: oak cabinets, walnut desks, plywood shelves. "
    "CNC router, edge bander, drill, assembly station, finishing/painting booth. "
    "3 product families sharing finishing as bottleneck, "
    "4 customer orders with various deadlines and penalty rates."
)


def generate(*, seed: int = 0) -> PlanningModel:
    """Generate the Furniture Manufacturing scenario.

    Args:
        seed: Random seed for variant generation.

    Returns:
        A PlanningModel for the scenario.
    """
    gen = ScenarioGenerator(seed=seed)
    return gen.generate(
        palette="furniture",
        num_machine_types=4,
        machines_per_type=2,  # 2 of each machine type
        bom_depth=3,
        num_raw_materials=4,
        num_final_products=2,
        rules_per_stage=2,     # 2 rules per stage for alternative routings
        num_operators=4,       # more operators
        num_orders=3,
        order_qty_range=(3, 12),
        duration_per_unit_range=(30, 180),
        duration_batch_range=(10, 45),
        batch_min=1,
        batch_max=6,
        horizon_days=40,
        setup_times=True,
    )
