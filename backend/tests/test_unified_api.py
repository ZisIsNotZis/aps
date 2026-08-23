"""Tests for the unified APS API."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from aps.api import app
from aps.unified._schema import (
    Entity,
    Objective,
    Order,
    PlanningModel,
    Rule,
    Selector,
)

client = TestClient(app)


def _simple_model() -> PlanningModel:
    """Minimal valid model."""
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


class TestUnifiedApi:
    def test_plan_endpoint_returns_solver_result(self) -> None:
        model = _simple_model()
        response = client.post("/api/unified/plan", json=model.model_dump(mode="json"))
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ("feasible", "optimal", "infeasible")
        assert "scheduled_blocks" in data
        assert "makespan_s" in data

    def test_plan_endpoint_has_scheduled_blocks(self) -> None:
        model = _simple_model()
        response = client.post("/api/unified/plan", json=model.model_dump(mode="json"))
        assert response.status_code == 200
        data = response.json()
        assert len(data["scheduled_blocks"]) > 0
        block = data["scheduled_blocks"][0]
        assert block["rule_id"] == "make_component"

    def test_plan_empty_model(self) -> None:
        model = PlanningModel(
            entities=[],
            rules=[],
            orders=[],
            objective=Objective(expression="$money_cent_remaining"),
            planning_start=datetime(2026, 7, 24, tzinfo=UTC),
            planning_horizon_s=86400,
        )
        response = client.post("/api/unified/plan", json=model.model_dump(mode="json"))
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "feasible"
        assert len(data["scheduled_blocks"]) == 0

    def test_validate_endpoint_valid(self) -> None:
        model = _simple_model()
        response = client.post("/api/unified/validate", json=model.model_dump(mode="json"))
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["errors"]) == 0

    def test_validate_endpoint_invalid(self) -> None:
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
        response = client.post("/api/unified/validate", json=model.model_dump(mode="json"))
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_plan_invalid_model_returns_422(self) -> None:
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
        response = client.post("/api/unified/plan", json=model.model_dump(mode="json"))
        assert response.status_code == 422
