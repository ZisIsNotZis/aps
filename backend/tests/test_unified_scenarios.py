"""Tests for the unified APS scenarios."""

from __future__ import annotations

from fastapi.testclient import TestClient

from aps.api import app
from aps.unified._compile import compile_model
from aps.unified.scenarios import _discrete
from aps.unified.scenarios.registry import get_scenario, list_scenarios

client = TestClient(app)


class TestScenarioRegistry:
    def test_list_scenarios_returns_known(self) -> None:
        scenarios = list_scenarios()
        assert len(scenarios) >= 1
        ids = [s.scenario_id for s in scenarios]
        assert "discrete_manufacturing" in ids

    def test_get_scenario_discrete_returns_model(self) -> None:
        model = get_scenario("discrete_manufacturing")
        assert model is not None
        total_entities = sum(e.count for e in model.entities)
        assert total_entities >= 6
        assert len(model.rules) == 1
        assert len(model.orders) == 1

    def test_get_scenario_unknown_returns_none(self) -> None:
        model = get_scenario("unknown_scenario")
        assert model is None

    def test_scenario_compiles_successfully(self) -> None:
        model = _discrete.generate()
        compiled = compile_model(model)
        assert len(compiled.rules) == 1
        assert len(compiled.orders) == 1
        assert "steel_kg" in compiled.initial_entities


class TestScenarioApi:
    def test_scenarios_endpoint_lists_known(self) -> None:
        response = client.get("/api/unified/scenarios")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        ids = [s["scenario_id"] for s in data]
        assert "discrete_manufacturing" in ids

    def test_get_scenario_endpoint_returns_model(self) -> None:
        response = client.get("/api/unified/scenarios/discrete_manufacturing")
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert "rules" in data
        assert "orders" in data

    def test_get_scenario_endpoint_unknown_returns_404(self) -> None:
        response = client.get("/api/unified/scenarios/unknown_scenario")
        assert response.status_code == 404
