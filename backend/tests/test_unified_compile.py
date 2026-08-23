"""Tests for the unified APS compiler — validate → normalize → compile."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from aps.unified._compile import CompileError, compile_model
from aps.unified._schema import (
    Entity,
    HoldingRule,
    Objective,
    Order,
    PlanningModel,
    Rule,
    Selector,
)


def _sample_model() -> PlanningModel:
    """Minimal valid discrete manufacturing model."""
    return PlanningModel(
        entities=[
            Entity(fields={"type": "steel_kg", "value": 500}),
            Entity(fields={"type": "cnc_machine", "state": "idle", "location": "plant_a"}),
            Entity(fields={"type": "operator", "location": "plant_a"}),
        ],
        rules=[
            Rule(
                rule_id="make_component",
                consume={"steel": Selector(conditions={"type": "steel_kg"})},
                consume_batch={"machine": Selector(conditions={"type": "cnc_machine", "state": "idle"})},
                produce={"component": Selector(conditions={"type": "component_each"})},
                produce_batch={"machine": Selector(conditions={"type": "cnc_machine", "state": "running"})},
                duration_s=60.0,
                duration_batch_s=10.0,
            ),
        ],
        orders=[
            Order(
                order_id="ORD-1",
                consume={"component": Selector(conditions={"type": "component_each"}, num=100)},
                deadline=datetime(2026, 8, 15, tzinfo=UTC),
                late_delivery_penalty_per_s=50,
            ),
        ],
        objective=Objective(expression="$money_cent_remaining"),
        planning_start=datetime(2026, 7, 24, tzinfo=UTC),
        planning_horizon_s=86400 * 30,
    )


class TestCompileModel:
    def test_valid_model_compiles(self) -> None:
        model = _sample_model()
        plan = compile_model(model)
        assert len(plan.rules) == 1
        assert plan.rules[0].rule_id == "make_component"
        assert len(plan.orders) == 1
        assert plan.horizon_ticks > 0
        assert "steel_kg" in plan.initial_entities

    def test_entities_grouped_by_type(self) -> None:
        model = PlanningModel(
            entities=[
                Entity(fields={"type": "steel_kg", "location": "plant_a"}),
                Entity(fields={"type": "steel_kg", "location": "plant_b"}),
                Entity(fields={"type": "component_each", "location": "plant_a"}),
            ],
            rules=[],
            orders=[],
            objective=Objective(expression="$money_cent_remaining"),
            planning_start=datetime(2026, 7, 24, tzinfo=UTC),
            planning_horizon_s=86400,
        )
        plan = compile_model(model)
        assert len(plan.initial_entities["steel_kg"]) == 2
        assert len(plan.initial_entities["component_each"]) == 1

    def test_compile_assigns_stable_ids(self) -> None:
        model = _sample_model()
        plan1 = compile_model(model)
        plan2 = compile_model(model)
        # Same input → same IDs
        assert plan1.rules[0].rule_id == plan2.rules[0].rule_id
        assert list(plan1.initial_entities.keys()) == list(plan2.initial_entities.keys())

    def test_duplicate_rule_ids_raises(self) -> None:
        model = PlanningModel(
            entities=[],
            rules=[
                Rule(rule_id="dup", consume={}, produce={}),
                Rule(rule_id="dup", consume={}, produce={}),
            ],
            orders=[],
            objective=Objective(expression="$money_cent_remaining"),
            planning_start=datetime(2026, 7, 24, tzinfo=UTC),
            planning_horizon_s=86400,
        )
        with pytest.raises(CompileError, match="duplicate"):
            compile_model(model)

    def test_duplicate_order_ids_raises(self) -> None:
        model = PlanningModel(
            entities=[],
            rules=[],
            orders=[
                Order(order_id="dup", consume={}),
                Order(order_id="dup", consume={}),
            ],
            objective=Objective(expression="$money_cent_remaining"),
            planning_start=datetime(2026, 7, 24, tzinfo=UTC),
            planning_horizon_s=86400,
        )
        with pytest.raises(CompileError, match="duplicate"):
            compile_model(model)

    def test_compiled_rule_has_expected_structure(self) -> None:
        model = _sample_model()
        plan = compile_model(model)
        rule = plan.rules[0]
        assert rule.rule_id == "make_component"
        assert rule.batch_min == 1
        assert rule.batch_max == 100
        assert rule.duration_ticks > 0
        assert rule.duration_batch_ticks >= 0
        assert len(rule.consume) == 1
        assert len(rule.consume_batch) == 1
        assert len(rule.produce) == 1
        assert len(rule.produce_batch) == 1

    def test_compiled_order_has_deadline_ticks(self) -> None:
        model = _sample_model()
        plan = compile_model(model)
        order = plan.orders[0]
        assert order.order_id == "ORD-1"
        assert order.deadline_ticks > 0
        assert order.late_delivery_penalty_per_s == 50

    def test_holding_rule_compiled(self) -> None:
        model = PlanningModel(
            entities=[Entity(fields={"type": "steel_kg", "value": 500})],
            rules=[],
            orders=[],
            holding_rules=[
                HoldingRule(
                    selector=Selector(conditions={"type": "steel_kg"}),
                    max=10000,
                ),
            ],
            objective=Objective(expression="$money_cent_remaining"),
            planning_start=datetime(2026, 7, 24, tzinfo=UTC),
            planning_horizon_s=86400,
        )
        plan = compile_model(model)
        assert len(plan.holding_rules) == 1
        assert plan.holding_rules[0].max == 10000

    def test_empty_model_compiles(self) -> None:
        model = PlanningModel(
            entities=[],
            rules=[],
            orders=[],
            objective=Objective(expression="$money_cent_remaining"),
            planning_start=datetime(2026, 7, 24, tzinfo=UTC),
            planning_horizon_s=86400,
        )
        plan = compile_model(model)
        assert len(plan.rules) == 0
        assert len(plan.orders) == 0
        assert plan.horizon_ticks > 0
