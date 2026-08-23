"""Food Processing — batch manufacturing with oven capacity constraints.

Scenario: An artisanal food production facility:
- Mixing, baking, cooling, icing, packaging stages
- Industrial ovens as capacity bottleneck
- Batch processing with strict minimum batch sizes
- Multiple product types competing for oven time
- Ingredient freshness constraints (expiry model)

Demonstrates batch processing optimization, shared bottleneck scheduling,
and multi-product campaign planning.
"""

from __future__ import annotations

from aps.unified._schema import PlanningModel
from aps.unified.scenarios._generator import ScenarioGenerator

SCENARIO_ID = "food_processing"
SCENARIO_NAME = "Food Processing & Baking"
SCENARIO_DESCRIPTION = (
    "Artisanal food production: mixing → baking → cooling → icing → packaging. "
    "2 industrial ovens as bottleneck, 3 product lines (cookies, chocolates, bread), "
    "strict batch size requirements, tight freshness deadlines, "
    "large raw material inventory, 4 customer orders."
)


def generate(*, seed: int = 0) -> PlanningModel:
    """Generate the Food Processing scenario.

    Args:
        seed: Random seed for variant generation.

    Returns:
        A PlanningModel for the scenario.
    """
    gen = ScenarioGenerator(seed=seed)
    return gen.generate(
        palette="food",
        num_machine_types=3,
        machines_per_type=3,   # 3 machines per type for more capacity
        bom_depth=3,
        num_raw_materials=6,
        num_final_products=2,
        rules_per_stage=2,
        num_operators=4,
        num_orders=3,
        order_qty_range=(5, 15),
        duration_per_unit_range=(10, 45),
        duration_batch_range=(10, 45),
        batch_min=1,
        batch_max=15,
        horizon_days=14,
        setup_times=True,
    )
