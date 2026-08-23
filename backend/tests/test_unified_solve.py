"""Tests for the unified APS solver — greedy and CP-SAT."""

from __future__ import annotations

from datetime import UTC, datetime

from aps.unified._compile import compile_model
from aps.unified._schema import (
    Entity,
    Objective,
    Order,
    PlanningModel,
    Rule,
    Selector,
)
from aps.unified._solve import solve


def _simple_manufacturing_model() -> PlanningModel:
    """One machine, one rule, one order."""
    return PlanningModel(
        entities=[
            Entity(fields={"type": "steel_kg", "location": "plant_a"}),
            Entity(fields={"type": "steel_kg", "location": "plant_a"}),
            Entity(fields={"type": "steel_kg", "location": "plant_a"}),
            Entity(fields={"type": "steel_kg", "location": "plant_a"}),
            Entity(fields={"type": "steel_kg", "location": "plant_a"}),
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


class TestSolve:
    def test_simple_model_produces_result(self) -> None:
        model = _simple_manufacturing_model()
        compiled = compile_model(model)
        result = solve(compiled)
        assert result.status in ("feasible", "optimal")
        assert result.makespan_s > 0
        assert result.solver_time_s >= 0

    def test_simple_model_has_scheduled_blocks(self) -> None:
        model = _simple_manufacturing_model()
        compiled = compile_model(model)
        result = solve(compiled)
        assert len(result.scheduled_blocks) > 0
        block = result.scheduled_blocks[0]
        assert block.rule_id == "make_component"
        assert block.batch_qty > 0
        assert block.start_tick >= 0
        assert block.end_tick > block.start_tick

    def test_empty_model_produces_trivial_result(self) -> None:
        model = PlanningModel(
            entities=[],
            rules=[],
            orders=[],
            objective=Objective(expression="$money_cent_remaining"),
            planning_start=datetime(2026, 7, 24, tzinfo=UTC),
            planning_horizon_s=86400,
        )
        compiled = compile_model(model)
        result = solve(compiled)
        assert result.status in ("feasible", "optimal")
        assert len(result.scheduled_blocks) == 0

    def test_equipment_no_overlap_within_single_equipment(self) -> None:
        """Two rules using the same equipment should not overlap."""
        model = PlanningModel(
            entities=[
                Entity(fields={"type": "steel_kg", "location": "plant_a"}),
                Entity(fields={"type": "aluminum_kg", "location": "plant_a"}),
                Entity(fields={"type": "cnc_machine", "state": "idle"}),
            ],
            rules=[
                Rule(
                    rule_id="make_steel_part",
                    consume={"steel": Selector(conditions={"type": "steel_kg"})},
                    consume_batch={"machine": Selector(conditions={"type": "cnc_machine", "state": "idle"})},
                    produce={"part": Selector(conditions={"type": "steel_part_each"})},
                    produce_batch={"machine": Selector(conditions={"type": "cnc_machine", "state": "idle"})},
                    duration_s=60.0,
                ),
                Rule(
                    rule_id="make_alu_part",
                    consume={"alu": Selector(conditions={"type": "aluminum_kg"})},
                    consume_batch={"machine": Selector(conditions={"type": "cnc_machine", "state": "idle"})},
                    produce={"part": Selector(conditions={"type": "alu_part_each"})},
                    produce_batch={"machine": Selector(conditions={"type": "cnc_machine", "state": "idle"})},
                    duration_s=60.0,
                ),
            ],
            orders=[
                Order(
                    order_id="ORD-1",
                    consume={"part": Selector(conditions={"type": "steel_part_each"}, num=1)},
                    deadline=datetime(2026, 8, 15, tzinfo=UTC),
                ),
                Order(
                    order_id="ORD-2",
                    consume={"part": Selector(conditions={"type": "alu_part_each"}, num=1)},
                    deadline=datetime(2026, 8, 15, tzinfo=UTC),
                ),
            ],
            objective=Objective(expression="$money_cent_remaining"),
            planning_start=datetime(2026, 7, 24, tzinfo=UTC),
            planning_horizon_s=86400 * 30,
        )
        compiled = compile_model(model)
        result = solve(compiled)
        # All blocks should be scheduled on the same equipment without overlap
        blocks = sorted(result.scheduled_blocks, key=lambda b: b.start_tick)
        for i in range(len(blocks) - 1):
            assert blocks[i].end_tick <= blocks[i + 1].start_tick, (
                f"Block {blocks[i].rule_id} ends at {blocks[i].end_tick} "
                f"but next block starts at {blocks[i + 1].start_tick}"
            )

    def test_inventory_limits_batch_size(self) -> None:
        """With only 1 steel_kg, max batch is 1."""
        model = PlanningModel(
            entities=[
                Entity(fields={"type": "steel_kg", "location": "plant_a"}),
                Entity(fields={"type": "cnc_machine", "state": "idle"}),
            ],
            rules=[
                Rule(
                    rule_id="make_component",
                    consume={"steel": Selector(conditions={"type": "steel_kg"})},
                    consume_batch={"machine": Selector(conditions={"type": "cnc_machine", "state": "idle"})},
                    produce={"component": Selector(conditions={"type": "component_each"})},
                    produce_batch={"machine": Selector(conditions={"type": "cnc_machine", "state": "idle"})},
                    duration_s=60.0,
                    batch_max=100,
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
        compiled = compile_model(model)
        result = solve(compiled)
        # With 1 steel_kg, we can produce at most 1 component
        total_produced = sum(
            sum(e.num for e in b.produced if e.entity_type == "component_each")
            for b in result.scheduled_blocks
        )
        assert total_produced <= 1
