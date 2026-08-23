"""Unified APS API — compile, validate, and solve planning models."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from aps.unified._compile import CompileError, compile_model
from aps.unified._schema import PlanningModel  # noqa: TC001
from aps.unified._solve import SolverResult, solve
from aps.unified.scenarios.registry import ScenarioMeta, get_scenario, list_scenarios

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/unified")


@router.post("/plan")
def plan(model: PlanningModel) -> SolverResult:
    """Compile and solve the planning model.

    Args:
        model: The planning model to compile and solve.

    Returns:
        A SolverResult with scheduled blocks and order outcomes.
    """
    if not model.entities and not model.rules and not model.orders:
        logger.info("Empty planning model — returning trivial result")
        return SolverResult(
            status="feasible",
            scheduled_blocks=[],
            order_outcomes=[],
            makespan_s=0,
            solver_time_s=0.0,
        )

    try:
        compiled = compile_model(model)
    except CompileError as exc:
        logger.error("Compilation failed: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    logger.info(
        "Planning model compiled: %d rules, %d orders, %d entity types, %d ticks",
        len(compiled.rules),
        len(compiled.orders),
        len(compiled.initial_entities),
        compiled.horizon_ticks,
    )

    result = solve(compiled)
    logger.info(
        "Solved: status=%s, blocks=%d, makespan=%ds, time=%.2fs",
        result.status,
        len(result.scheduled_blocks),
        result.makespan_s,
        result.solver_time_s,
    )
    return result


@router.post("/validate")
def validate(model: PlanningModel) -> dict[str, object]:
    """Validate the planning model without solving.

    Args:
        model: The planning model to validate.

    Returns:
        A dict with 'valid' bool and optional 'errors' list.
    """
    errors: list[str] = []

    # Check for duplicate rule IDs
    rule_ids: set[str] = set()
    for r in model.rules:
        if r.rule_id in rule_ids:
            errors.append(f"Duplicate rule_id: {r.rule_id!r}")
        rule_ids.add(r.rule_id)

    # Check for duplicate order IDs
    order_ids: set[str] = set()
    for o in model.orders:
        if o.order_id in order_ids:
            errors.append(f"Duplicate order_id: {o.order_id!r}")
        order_ids.add(o.order_id)

    if errors:
        logger.warning("Validation failed: %s", "; ".join(errors))
        return {"valid": False, "errors": errors}

    try:
        compile_model(model)
    except CompileError as exc:
        logger.warning("Compilation failed during validation: %s", exc)
        return {"valid": False, "errors": [str(exc)]}

    logger.info("Validation passed: %d rules, %d orders", len(model.rules), len(model.orders))
    return {"valid": True, "errors": []}


@router.get("/scenarios", response_model=list[ScenarioMeta])
def list_scenarios_endpoint() -> list[ScenarioMeta]:
    """List all available scenario templates."""
    return list_scenarios()


@router.get("/scenarios/{scenario_id}")
def get_scenario_endpoint(scenario_id: str) -> PlanningModel:
    """Load a scenario by ID.

    Args:
        scenario_id: The scenario ID (e.g. "discrete_manufacturing").

    Returns:
        The PlanningModel for the scenario.

    Raises:
        HTTPException: If the scenario is not found.
    """
    model = get_scenario(scenario_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id!r}")
    return model
