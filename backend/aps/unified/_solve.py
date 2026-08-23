"""Solver dispatch — delegates to registered solver plugins.

Usage::

    from aps.unified._solve import solve, SolverResult, SolverConfig

    result = solve(plan)                         # uses default (greedy)
    result = solve(plan, SolverConfig(solver="greedy"))
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aps.unified._types import (
    EntitySnapshot,
    OrderOutcome,
    ScheduledBlock,
    SolverResult,
)

if TYPE_CHECKING:

    from aps.unified._compile import CompiledPlan

logger = logging.getLogger(__name__)


# ── Dispatch ────────────────────────────────────────────────────────────────


def solve(
    plan: CompiledPlan,
    config: object | None = None,
) -> SolverResult:
    """Solve the compiled planning problem.

    Dispatches to the solver named in *config*.  When *config* is
    ``None`` a default :class:`SolverConfig` with ``solver="greedy"``
    is used so that existing callers continue to work unchanged.

    Args:
        plan: The compiled planning problem.
        config: A ``SolverConfig`` instance, or ``None`` for defaults.

    Returns:
        A SolverResult with scheduled blocks and order outcomes.
    """
    # Late imports avoid circular dependencies.
    # Importing solvers.greedy triggers its _SOLVERS["greedy"] registration.
    import aps.unified.solvers.cp_sat
    import aps.unified.solvers.greedy
    import aps.unified.solvers.fluid  # noqa: F401 — registers "fluid" plugin
    # Optional solvers (may need extra dependencies)
    try:
        import aps.unified.solvers.gurobi  # noqa: F401 — needs gurobipy
    except ModuleNotFoundError:
        pass
    try:
        import aps.unified.solvers.timefold  # noqa: F401 — needs Java 21+
    except ModuleNotFoundError:
        pass
    from aps.unified.solvers import SolverConfig, run_solver

    if config is None:
        config = SolverConfig(horizon_ticks=plan.horizon_ticks)
    if config.objective_expression is None:  # type: ignore[union-attr]
        config.objective_expression = plan.objective_expression  # type: ignore[union-attr]

    logger.info(
        "Solving %d rules, %d orders, %d entity types over %d ticks (solver=%s)",
        len(plan.rules),
        len(plan.orders),
        len(plan.initial_entities),
        plan.horizon_ticks,
        config.solver,  # type: ignore[union-attr]
    )

    return run_solver(plan, config)  # type: ignore[arg-type]
