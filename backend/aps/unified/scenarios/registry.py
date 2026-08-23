"""Scenario registry — discover and load scenarios."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from aps.unified._schema import PlanningModel
from aps.unified.scenarios import (
    _assembly_line,
    _automotive,
    _discrete,
    _electronics,
    _food,
    _furniture,
    _job_shop,
    _pharma,
    _semiconductor,
)

ScenarioGenerator = Callable[..., PlanningModel]


@dataclass(frozen=True)
class ScenarioMeta:
    """Metadata for a scenario."""

    scenario_id: str
    name: str
    description: str


# Registry of all available scenarios
_REGISTRY: dict[str, tuple[ScenarioMeta, ScenarioGenerator]] = {
    _discrete.SCENARIO_ID: (
        ScenarioMeta(
            scenario_id=_discrete.SCENARIO_ID,
            name=_discrete.SCENARIO_NAME,
            description=_discrete.SCENARIO_DESCRIPTION,
        ),
        _discrete.generate,
    ),
    _electronics.SCENARIO_ID: (
        ScenarioMeta(
            scenario_id=_electronics.SCENARIO_ID,
            name=_electronics.SCENARIO_NAME,
            description=_electronics.SCENARIO_DESCRIPTION,
        ),
        _electronics.generate,
    ),
    _job_shop.SCENARIO_ID: (
        ScenarioMeta(
            scenario_id=_job_shop.SCENARIO_ID,
            name=_job_shop.SCENARIO_NAME,
            description=_job_shop.SCENARIO_DESCRIPTION,
        ),
        _job_shop.generate,
    ),
    _assembly_line.SCENARIO_ID: (
        ScenarioMeta(
            scenario_id=_assembly_line.SCENARIO_ID,
            name=_assembly_line.SCENARIO_NAME,
            description=_assembly_line.SCENARIO_DESCRIPTION,
        ),
        _assembly_line.generate,
    ),
    _automotive.SCENARIO_ID: (
        ScenarioMeta(
            scenario_id=_automotive.SCENARIO_ID,
            name=_automotive.SCENARIO_NAME,
            description=_automotive.SCENARIO_DESCRIPTION,
        ),
        _automotive.generate,
    ),
    _furniture.SCENARIO_ID: (
        ScenarioMeta(
            scenario_id=_furniture.SCENARIO_ID,
            name=_furniture.SCENARIO_NAME,
            description=_furniture.SCENARIO_DESCRIPTION,
        ),
        _furniture.generate,
    ),
    _food.SCENARIO_ID: (
        ScenarioMeta(
            scenario_id=_food.SCENARIO_ID,
            name=_food.SCENARIO_NAME,
            description=_food.SCENARIO_DESCRIPTION,
        ),
        _food.generate,
    ),
    _pharma.SCENARIO_ID: (
        ScenarioMeta(
            scenario_id=_pharma.SCENARIO_ID,
            name=_pharma.SCENARIO_NAME,
            description=_pharma.SCENARIO_DESCRIPTION,
        ),
        _pharma.generate,
    ),
    _semiconductor.SCENARIO_ID: (
        ScenarioMeta(
            scenario_id=_semiconductor.SCENARIO_ID,
            name=_semiconductor.SCENARIO_NAME,
            description=_semiconductor.SCENARIO_DESCRIPTION,
        ),
        _semiconductor.generate,
    ),
}


def list_scenarios() -> list[ScenarioMeta]:
    """List all available scenarios."""
    return [meta for meta, _ in _REGISTRY.values()]


def get_scenario(scenario_id: str) -> PlanningModel | None:
    """Load a scenario by ID.

    Args:
        scenario_id: The scenario ID (e.g. "discrete_manufacturing").

    Returns:
        The PlanningModel, or None if the scenario is not found.
    """
    entry = _REGISTRY.get(scenario_id)
    if entry is None:
        return None
    _, generator = entry
    return generator(seed=0)
