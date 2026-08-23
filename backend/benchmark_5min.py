"""5-minute benchmark — compare cp_sat, gurobi, timefold on 4 scenarios.

Each solver runs for 300s per scenario, recording intermediate solution
quality (decay curve). Results are saved to docs/solver_benchmark_5min.json.

Usage::

    cd backend && python benchmark_5min.py
"""

from __future__ import annotations

import json
import logging
import sys
import time

from aps.unified._compile import compile_model
from aps.unified._solve import solve, SolverResult
from aps.unified.solvers import SolverConfig
from aps.unified.scenarios.registry import get_scenario, list_scenarios

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("benchmark")

# ── Configuration ──────────────────────────────────────────────────────────

# Scenarios to run (the 4 most representative across scales)
SCENARIO_IDS = [
    "discrete_manufacturing",  # tiny, warm-up
    "electronics_smt",         # medium, high material complexity
    "job_shop",                # medium, routing complexity
    "pharma_manufacturing",    # large, continuous process
]

# Solver backends to test
SOLVERS = ["cp_sat", "gurobi", "timefold"]

# Time limit per solver per scenario (seconds)
TIME_LIMIT_S = 300

# Output file (relative to project root)
OUTPUT_PATH = "docs/solver_benchmark_5min.json"


def compute_metrics(
    plan: object,
    result: SolverResult,
) -> dict:
    """Compute summary metrics from a solver result."""
    blocks = result.scheduled_blocks
    outcomes = result.order_outcomes
    fulfilled = sum(1 for o in outcomes if o.fulfilled)
    total_orders = len(outcomes)

    # Compute makespan in seconds
    makespan_s = result.makespan_s

    # Compute total lateness
    total_late_ticks = sum(o.lateness_ticks for o in outcomes)

    # Score: lower is better (shortfall * penalty + makespan)
    score = 0
    for o in outcomes:
        if not o.fulfilled:
            score += 10_000_000  # approximate penalty for unfulfilled
    score += makespan_s

    return {
        "blocks": len(blocks),
        "makespan_s": makespan_s,
        "fulfilled": fulfilled,
        "total_orders": total_orders,
        "fulfillment_pct": round(fulfilled / max(total_orders, 1) * 100, 1),
        "total_lateness_ticks": total_late_ticks,
        "score": score,
        "solver_time_s": round(result.solver_time_s, 3),
        "status": result.status,
    }


def main() -> None:
    results: dict[str, dict[str, dict]] = {}
    start_time = time.monotonic()

    # Verify scenarios exist
    available = {s.scenario_id for s in list_scenarios()}
    for sid in SCENARIO_IDS:
        if sid not in available:
            logger.warning("Scenario %r not found, skipping", sid)

    for sid in SCENARIO_IDS:
        if sid not in available:
            continue

        logger.info("─" * 60)
        logger.info("Scenario: %s", sid)
        model = get_scenario(sid)
        if model is None:
            logger.warning("  Failed to load scenario %s, skipping", sid)
            continue

        plan = compile_model(model)
        logger.info(
            "  Rules=%d, Orders=%d, EntityTypes=%d, Horizon=%d ticks",
            len(plan.rules),
            len(plan.orders),
            len(plan.initial_entities),
            plan.horizon_ticks,
        )

        scenario_results: dict[str, dict] = {}

        for solver_name in SOLVERS:
            logger.info("  Solver: %s", solver_name)
            solver_start = time.monotonic()

            try:
                result = solve(
                    plan,
                    SolverConfig(
                        solver=solver_name,
                        time_limit_s=TIME_LIMIT_S,
                        horizon_ticks=plan.horizon_ticks,
                    ),
                )
            except Exception as e:
                logger.error("  Solver %s failed: %s", solver_name, e)
                scenario_results[solver_name] = {
                    "error": str(e),
                    "metrics": None,
                    "solution_curve": [],
                    "wall_time_s": round(time.monotonic() - solver_start, 3),
                }
                continue

            wall_time_s = round(time.monotonic() - solver_start, 3)
            metrics = compute_metrics(plan, result)
            metrics["wall_time_s"] = wall_time_s

            # Normalize solution curve
            curve = list(result.solution_curve) if result.solution_curve else []

            logger.info(
                "    → %d blocks, %d/%d orders, %ds makespan, %.1fs wall, curve=%d pts",
                metrics["blocks"],
                metrics["fulfilled"],
                metrics["total_orders"],
                metrics["makespan_s"],
                wall_time_s,
                len(curve),
            )

            scenario_results[solver_name] = {
                "metrics": metrics,
                "solution_curve": curve,
                "wall_time_s": wall_time_s,
            }

        results[sid] = scenario_results

        # Save incremental results
        _save_results(results, start_time)

    _save_results(results, start_time)
    logger.info("=" * 60)
    logger.info("Benchmark complete in %.1f seconds", time.monotonic() - start_time)


def _save_results(results: dict, bench_start: float) -> None:
    """Save benchmark results to JSON file."""
    import os

    # Ensure docs directory exists
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    payload = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "time_limit_s": TIME_LIMIT_S,
        "solvers": SOLVERS,
        "scenarios": SCENARIO_IDS,
        "results": results,
        "total_wall_time_s": round(time.monotonic() - bench_start, 3),
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    logger.info("  Results saved to %s", OUTPUT_PATH)


if __name__ == "__main__":
    main()