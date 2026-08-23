"""Tests for the unified APS schema — strictly typed, zero Any."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from aps.unified._schema import (
    Entity,
    HoldingRule,
    Objective,
    Order,
    PlanningModel,
    Rule,
    Selector,
)


class TestEntity:
    def test_entity_with_scalar_fields(self) -> None:
        e = Entity(fields={"type": "steel_kg", "location": "plant_a", "value": 500, "price": 650})
        assert e.fields["type"] == "steel_kg"
        assert e.fields["value"] == 500

    def test_entity_with_expiry_datetime(self) -> None:
        dt = datetime(2026, 8, 20, tzinfo=UTC)
        e = Entity(fields={"type": "steel_kg", "expiry": dt})
        assert e.fields["expiry"] == dt

    def test_entity_rejects_nested_dict(self) -> None:
        with pytest.raises(ValidationError, match="must be scalar"):
            Entity(fields={"type": "steel_kg", "nested": {"a": 1}})

    def test_entity_rejects_nested_list(self) -> None:
        with pytest.raises(ValidationError, match="must be scalar"):
            Entity(fields={"type": "steel_kg", "tags": ["a", "b"]})

    def test_entity_with_lifetime_field(self) -> None:
        e = Entity(fields={"type": "tool", "lifetime": 100})
        assert e.fields["lifetime"] == 100

    def test_entity_with_datetimeexpr_field(self) -> None:
        e = Entity(fields={"type": "shift", "datetimeexpr": "RRULE:FREQ=WEEKLY;BYDAY=MO"})
        assert e.fields["datetimeexpr"] == "RRULE:FREQ=WEEKLY;BYDAY=MO"


class TestSelector:
    def test_selector_with_scalar_conditions(self) -> None:
        s = Selector(conditions={"type": "steel_kg", "location": "plant_a"}, num=2.0)
        assert s.conditions["type"] == "steel_kg"
        assert s.num == 2.0

    def test_selector_default_num(self) -> None:
        s = Selector(conditions={"type": "steel_kg"})
        assert s.num == 1.0

    def test_selector_with_expression_condition(self) -> None:
        s = Selector(conditions={"expiry": "$top.expiry"})
        assert s.conditions["expiry"] == "$top.expiry"

    def test_selector_rejects_nested_conditions(self) -> None:
        with pytest.raises(ValidationError, match="must be scalar"):
            Selector(conditions={"type": "steel_kg", "nested": {"a": 1}})


class TestRule:
    def test_minimal_rule(self) -> None:
        r = Rule(
            rule_id="make_component",
            consume={"steel": Selector(conditions={"type": "steel_kg"})},
            produce={"component": Selector(conditions={"type": "component_each"})},
        )
        assert r.rule_id == "make_component"
        assert r.batch_min == 1
        assert r.batch_max == 100

    def test_rule_with_batch_consume(self) -> None:
        r = Rule(
            rule_id="make_burger",
            consume={"patty": Selector(conditions={"type": "patty"})},
            consume_batch={"crew": Selector(conditions={"type": "boh_crew"})},
            produce={"burger": Selector(conditions={"type": "burger"})},
            produce_batch={"crew": Selector(conditions={"type": "boh_crew"})},
            duration_s=5.0,
            duration_batch_s=10.0,
        )
        assert r.consume_batch["crew"].conditions["type"] == "boh_crew"
        assert r.duration_s == 5.0

    def test_rule_with_batch_limits(self) -> None:
        r = Rule(
            rule_id="batch_rule",
            batch_min=10,
            batch_max=500,
            consume={"input": Selector(conditions={"type": "input"})},
            produce={"output": Selector(conditions={"type": "output"})},
        )
        assert r.batch_min == 10
        assert r.batch_max == 500


class TestOrder:
    def test_order_with_deadline(self) -> None:
        dt = datetime(2026, 7, 30, 17, 0, tzinfo=UTC)
        o = Order(
            order_id="ORD-1001",
            consume={"finished_phone": Selector(conditions={"type": "phone_v1_each"})},
            deadline=dt,
            late_delivery_penalty_per_s=100,
        )
        assert o.deadline == dt
        assert o.late_delivery_penalty_per_s == 100

    def test_order_with_no_deadline(self) -> None:
        o = Order(
            order_id="ORD-INF",
            consume={"finished_phone": Selector(conditions={"type": "phone_v1_each"})},
        )
        assert o.deadline is None

    def test_order_with_release_at(self) -> None:
        release = datetime(2026, 7, 28, tzinfo=UTC)
        deadline = datetime(2026, 7, 30, 17, 0, tzinfo=UTC)
        o = Order(
            order_id="ORD-1002",
            consume={"finished_phone": Selector(conditions={"type": "phone_v1_each"})},
            deadline=deadline,
            release_at=release,
        )
        assert o.release_at == release


class TestHoldingRule:
    def test_holding_rule_with_max(self) -> None:
        hr = HoldingRule(
            selector=Selector(conditions={"type": "steel_kg"}),
            max=1000,
        )
        assert hr.max == 1000
        assert hr.consume is None

    def test_holding_rule_with_ongoing_consumption(self) -> None:
        hr = HoldingRule(
            selector=Selector(conditions={"type": "equipment", "state": "idle"}),
            consume={"money": Selector(conditions={"type": "money_cent"}, num=10)},
            duration_s=3600,
        )
        assert hr.consume is not None
        assert hr.consume["money"].num == 10
        assert hr.duration_s == 3600


class TestObjective:
    def test_objective_default(self) -> None:
        obj = Objective(expression="$money_cent_remaining")
        assert obj.expression == "$money_cent_remaining"
        assert obj.expiry_loss_decay_factor == 0.5

    def test_objective_custom_decay(self) -> None:
        obj = Objective(expression="$money_cent_remaining", expiry_loss_decay_factor=0.8)
        assert obj.expiry_loss_decay_factor == 0.8


class TestPlanningModel:
    def test_valid_planning_model(self) -> None:
        model = PlanningModel(
            entities=[
                Entity(fields={"type": "steel_kg", "value": 500}),
                Entity(fields={"type": "cnc_machine", "state": "idle"}),
            ],
            rules=[
                Rule(
                    rule_id="make_component",
                    consume={"steel": Selector(conditions={"type": "steel_kg"})},
                    consume_batch={"machine": Selector(conditions={"type": "cnc_machine", "state": "idle"})},
                    produce={"component": Selector(conditions={"type": "component_each"})},
                    produce_batch={"machine": Selector(conditions={"type": "cnc_machine", "state": "running"})},
                    duration_s=60.0,
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
            holding_rules=[
                HoldingRule(
                    selector=Selector(conditions={"type": "steel_kg"}),
                    max=10000,
                ),
            ],
            objective=Objective(expression="$money_cent_remaining"),
            planning_start=datetime(2026, 7, 24, tzinfo=UTC),
            planning_horizon_s=86400 * 30,
        )
        assert len(model.entities) == 2
        assert len(model.rules) == 1
        assert len(model.orders) == 1
        assert len(model.holding_rules) == 1
        assert model.planning_horizon_s == 86400 * 30

    def test_planning_model_with_replanning(self) -> None:
        model = PlanningModel(
            entities=[],
            rules=[],
            orders=[],
            objective=Objective(expression="$money_cent_remaining"),
            planning_start=datetime(2026, 7, 24, tzinfo=UTC),
            planning_horizon_s=86400,
            completed_operations=[
                {"rule_id": "make_component", "start_tick": 0, "end_tick": 10, "batch_qty": 5},
            ],
            locked_operations=[
                {"rule_id": "assemble", "start_tick": 10, "end_tick": 20, "batch_qty": 5},
            ],
            freeze_fence_s=3600,
        )
        assert len(model.completed_operations) == 1
        assert len(model.locked_operations) == 1
        assert model.freeze_fence_s == 3600
