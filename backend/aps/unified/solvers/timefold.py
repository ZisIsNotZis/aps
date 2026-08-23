"""Timefold solver plugin — spawns Java Timefold sidecar via Maven.

Registered as ``"timefold"`` solver plugin.

Caveats:
- Requires Java 21+ and Maven (first run downloads many dependencies).
- JVM startup + model build adds 5-15s overhead per solve.
- Material balance and order fulfillment are evaluated post-solve in Python.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import time
from typing import TYPE_CHECKING

from aps.unified.solvers import _SOLVERS

if TYPE_CHECKING:

    from aps.unified._compile import CompiledPlan, CompiledRule
    from aps.unified._types import OrderOutcome, ScheduledBlock, SolverResult
    from aps.unified.solvers import SolverConfig

logger = logging.getLogger(__name__)

TIMEFOLD_DIR = os.path.join(os.path.dirname(__file__), "timefold")
JAR_PATH = os.path.join(TIMEFOLD_DIR, "target", "timefold-solver-1.0.jar")


def _build_problem_json(
    plan: CompiledPlan,
    time_limit_s: float,
) -> dict:
    """Convert CompiledPlan to the JSON format expected by the Java solver."""
    # Collect equipment type → entity ID mapping
    eq_ids: dict[str, list[str]] = {}
    for sig, entities in plan.initial_entities.items():
        # First entity in each type pool defines the type name
        if entities:
            eq_ids[sig] = [e.entity_id for e in entities]

    rules_json = []
    for r in plan.rules:
        # Find equipment type from consume_batch
        eq_type = ""
        for _, sel in r.consume_batch:
            t = sel.conditions.get("type")
            if isinstance(t, str):
                eq_type = t
                break

        consume_dict: dict[str, int] = {}
        for _, sel in r.consume:
            t = sel.conditions.get("type")
            if isinstance(t, str):
                consume_dict[t] = int(sel.num)
        produce_dict: dict[str, int] = {}
        for _, sel in r.produce:
            t = sel.conditions.get("type")
            if isinstance(t, str):
                produce_dict[t] = int(sel.num)

        rules_json.append({
            "ruleId": r.rule_id,
            "batchMin": r.batch_min,
            "batchMax": r.batch_max,
            "durationTicks": r.duration_ticks,
            "durationBatchTicks": r.duration_batch_ticks,
            "equipmentType": eq_type,
            "consume": consume_dict,
            "produce": produce_dict,
        })

    orders_json = []
    for o in plan.orders:
        for _, sel in o.consume:
            t = sel.conditions.get("type")
            if isinstance(t, str):
                orders_json.append({
                    "orderId": o.order_id,
                    "type": t,
                    "needed": int(sel.num),
                    "deadlineTicks": o.deadline_ticks,
                    "latePenaltyPerTick": o.late_delivery_penalty_per_s * 60,
                })

    initial_counts = {
        t: len(ents) for t, ents in plan.initial_entities.items()
    }

    return {
        "rules": rules_json,
        "orders": orders_json,
        "initialEntities": initial_counts,
        "horizonTicks": plan.horizon_ticks,
        "timeLimitSeconds": time_limit_s,
    }


def solve_timefold(
    plan: CompiledPlan,
    config: SolverConfig,
) -> SolverResult:
    """Solve with Timefold via Maven subprocess."""
    from aps.unified._evaluate import evaluate_fulfillment

    start_time = time.monotonic()

    # ── Write problem JSON ──────────────────────────────────────────────
    with tempfile.TemporaryDirectory(prefix="timefold_") as tmpdir:
        problem_path = os.path.join(tmpdir, "problem.json")
        solution_path = os.path.join(tmpdir, "solution.json")

        problem = _build_problem_json(plan, config.time_limit_s)
        with open(problem_path, "w") as f:
            json.dump(problem, f, indent=2)

        # ── Run Timefold JAR ────────────────────────────────────────────
        jar_path = os.path.join(TIMEFOLD_DIR, "target", "timefold-solver-1.0.jar")
        if not os.path.exists(jar_path):
            logger.warning("Timefold: JAR not built at %s, rebuilding...", jar_path)
            subprocess.run(["mvn", "package", "-DskipTests", "-q"],
                           cwd=TIMEFOLD_DIR, capture_output=True, timeout=300)

        logger.info("Timefold: running solver...")
        result = subprocess.run(
            ["java", "-jar", jar_path, problem_path, solution_path, str(config.time_limit_s)],
            capture_output=True, text=True,
            timeout=max(300, int(config.time_limit_s) + 60),
        )

        if result.returncode != 0:
            logger.warning("Timefold: Maven failed (rc=%d)\n%s\n%s",
                           result.returncode, result.stdout[:500], result.stderr[:500])
            return SolverResult(
                status="timeout",
                scheduled_blocks=[],
                order_outcomes=[],
                makespan_s=0,
                solver_time_s=time.monotonic() - start_time,
            )

        # ── Parse solution ──────────────────────────────────────────────
        try:
            with open(solution_path) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning("Timefold: failed to read solution: %s", e)
            return SolverResult(
                status="timeout",
                scheduled_blocks=[],
                order_outcomes=[],
                makespan_s=0,
                solver_time_s=time.monotonic() - start_time,
            )

    # ── Convert to ScheduledBlock[] ──────────────────────────────────────
    scheduled_blocks: list[ScheduledBlock] = []
    for b in data.get("blocks", []):
        scheduled_blocks.append(
            ScheduledBlock(
                rule_id=b["ruleId"],
                start_tick=b["startTick"],
                end_tick=b["endTick"],
                batch_qty=b["batchQty"],
                equipment_entity_id=b.get("equipmentId", "unknown"),
                consumed=[],
                produced=[],
            )
        )

    # ── Compute order outcomes via shared evaluation ────────────────────
    order_outcomes, max_end_tick, _, _ = evaluate_fulfillment(plan, scheduled_blocks)

    status_str = data.get("status", "feasible")
    solution_curve = data.get("solutionCurve", [])
    solver_time_s = time.monotonic() - start_time

    logger.info(
        "Timefold: %d blocks, %d/%d orders, %ds makespan, %.2fs",
        len(scheduled_blocks),
        sum(1 for o in order_outcomes if o.fulfilled),
        len(order_outcomes),
        max_end_tick * 60,
        solver_time_s,
    )

    return SolverResult(
        status=status_str,
        scheduled_blocks=scheduled_blocks,
        order_outcomes=order_outcomes,
        makespan_s=max_end_tick * 60,
        solver_time_s=solver_time_s,
        solution_curve=solution_curve,
    )


_SOLVERS["timefold"] = solve_timefold
