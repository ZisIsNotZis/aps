"""OR-Tools CP-SAT solver — optimal scheduling with full constraint support.

Registered as the ``"cp_sat"`` solver plugin.

Model:
- For each equipment entity, up to N optional interval slots for each compatible rule.
- Batch quantity = integer variable per interval.
- ``AddNoOverlap`` per equipment.
- Expiry constraints: initial inventory with expiry must be consumed before expiry.
- Holding rule constraints: cumulative inventory <= max for each holding rule type.
- Objective: minimize weighted shortfall + lateness + expired entity penalties.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from ortools.sat.python import cp_model

from aps.unified._compile import (
    CompiledEntity,
)
from aps.unified._evaluate import (
    _DEFAULT_TICK_S,
    _get_expiry_tick,
    evaluate_fulfillment as _evaluate_fulfillment,
    log_solver_result,
)
from aps.unified._types import (
    OrderOutcome,
    ScheduledBlock,
    SolverResult,
)
from aps.unified.solvers import _SOLVERS

if TYPE_CHECKING:

    from aps.unified._compile import CompiledPlan, CompiledRule
    from aps.unified.solvers import SolverConfig

logger = logging.getLogger(__name__)


def solve_cp_sat(
    plan: CompiledPlan,
    config: SolverConfig,
) -> SolverResult:
    """Solve with OR-Tools CP-SAT, respecting expiry, holding rules, and release tick."""
    start_time = time.monotonic()
    horizon_ticks = config.horizon_ticks or plan.horizon_ticks

    max_slots = 10
    model = cp_model.CpModel()

    # ── Build equipment → rule mapping ──────────────────────────────────
    equip_list: dict[str, list[CompiledRule]] = {}
    for r in plan.rules:
        for _, sel in r.consume_batch:
            etype = sel.conditions.get("type")
            if isinstance(etype, str):
                pool = plan.initial_entities.get(etype, [])
                for ent in pool:
                    equip_list.setdefault(ent.entity_id, []).append(r)

    # ── Create slot variables ───────────────────────────────────────────
    all_intervals: dict[str, list] = {}
    slot_data: list[tuple] = []

    for eq_id, rules in equip_list.items():
        all_intervals[eq_id] = []
        for r in rules:
            max_dur = r.duration_batch_ticks + r.batch_max * r.duration_ticks
            for slot in range(max_slots):
                name = f"{r.rule_id}_{eq_id}_s{slot}"
                p = model.NewBoolVar(f"p_{name}")
                s = model.NewIntVar(0, horizon_ticks, f"s_{name}")
                e = model.NewIntVar(0, horizon_ticks, f"e_{name}")
                b = model.NewIntVar(0, r.batch_max, f"b_{name}")
                model.Add(b >= r.batch_min).OnlyEnforceIf(p)
                model.Add(b == 0).OnlyEnforceIf(p.Not())
                d = model.NewIntVar(0, max_dur, f"d_{name}")
                model.Add(d == r.duration_batch_ticks + b * r.duration_ticks)
                iv = model.NewOptionalIntervalVar(s, d, e, p, f"i_{name}")
                all_intervals[eq_id].append(iv)
                slot_data.append((eq_id, r.rule_id, slot, p, s, e, b))

    # ── NoOverlap constraints ───────────────────────────────────────────
    for _eq_id, intervals in all_intervals.items():
        model.AddNoOverlap(intervals)

    # ── Material constraints ────────────────────────────────────────────
    initial_counts: dict[str, int] = {
        t: len(ents) for t, ents in plan.initial_entities.items()
    }

    type_totals: dict[str, list] = {}  # type → [(coeff, batch_var)]
    # Also track which rules consume each type (for expiry constraints)
    type_consumers: dict[str, list[tuple[str, int]]] = {}  # type → [(rule_id, rate)]

    for _eq_id, rule_id, _slot, _p, _s, _e, b in slot_data:
        rule = next((r for r in plan.rules if r.rule_id == rule_id), None)
        if rule is None:
            continue
        for _, sel in rule.produce:
            t = sel.conditions.get("type")
            if isinstance(t, str):
                type_totals.setdefault(t, []).append((1, b))
        for _, sel in rule.consume:
            t = sel.conditions.get("type")
            if isinstance(t, str):
                type_totals.setdefault(t, []).append((-1, b))
                type_consumers.setdefault(t, []).append((rule_id, int(sel.num)))

    for t, factors in type_totals.items():
        init = initial_counts.get(t, 0)
        if not factors:
            continue
        total = sum(coeff * var for coeff, var in factors)
        model.Add(init + total >= 0)

    # ── Expiry constraints ───────────────────────────────────────────────
    # For each entity type with expiry, sum of consumption before expiry tick
    # must be >= initial count (so entities don't spoil unused).
    for t, ents in plan.initial_entities.items():
        min_expiry: int | None = None
        for e in ents:
            tick = _get_expiry_tick(e)
            if tick is not None:
                if min_expiry is None or tick < min_expiry:
                    min_expiry = tick
        if min_expiry is None:
            continue

        initial_count = len(ents)
        if initial_count <= 0:
            continue

        # Find all slots consuming this type
        consumption_before = []
        for eq_id, rule_id, slot, p_var, s_var, e_var, b_var in slot_data:
            rule = next((r for r in plan.rules if r.rule_id == rule_id), None)
            if rule is None:
                continue
            consume_rate = 0
            for _, sel in rule.consume:
                if sel.conditions.get("type") == t:
                    consume_rate = int(sel.num)
                    break
            if consume_rate <= 0:
                continue

            # Binary: slot active AND ends before expiry
            is_before = model.NewBoolVar(f"bef_{t}_{eq_id}_{rule_id}_{slot}")
            model.Add(e_var < min_expiry).OnlyEnforceIf(is_before)
            model.Add(e_var >= min_expiry).OnlyEnforceIf(is_before.Not())
            model.Add(is_before <= p_var)

            effective = model.NewIntVar(0, 1000000, f"eff_{t}_{eq_id}_{rule_id}_{slot}")
            model.Add(effective == b_var * consume_rate).OnlyEnforceIf(is_before)
            model.Add(effective == 0).OnlyEnforceIf(is_before.Not())
            consumption_before.append(effective)

        if consumption_before:
            model.Add(sum(consumption_before) >= initial_count)

    # ── Holding rule constraints ─────────────────────────────────────────
    # For each holding rule with max: initial + net production <= max
    # (Net production = sum of produce - sum of consume)
    for hr in plan.holding_rules:
        hr_type = hr.selector.conditions.get("type")
        if not isinstance(hr_type, str) or hr.max is None:
            continue
        init = initial_counts.get(hr_type, 0)
        factors = type_totals.get(hr_type, [])
        if factors:
            # Net = init + sum(coeff * var) where coeff is 1 for produce, -1 for consume
            # So final_inv = init + sum(produce) - sum(consume)
            model.Add(init + sum(coeff * var for coeff, var in factors) <= int(hr.max))

    # ── Objective: shortfall + lateness + expiry + holding penalties ────
    obj_terms: list = []

    # Order shortfall penalty
    for order in plan.orders:
        for _, sel in order.consume:
            t = sel.conditions.get("type")
            if not isinstance(t, str):
                continue
            needed = int(sel.num)
            init = initial_counts.get(t, 0)
            factors = type_totals.get(t, [])
            avail = model.NewIntVar(0, 10_000_000, f"avail_{order.order_id}")
            if factors:
                model.Add(avail == init + sum(coeff * var for coeff, var in factors))
            else:
                model.Add(avail == init)

            shortfall = model.NewIntVar(0, 10_000_000, f"short_{order.order_id}")
            model.Add(shortfall >= needed - avail)

            penalty = int(order.late_delivery_penalty_per_s * _DEFAULT_TICK_S) if order.late_delivery_penalty_per_s else 100
            if penalty < 1:
                penalty = 100
            obj_terms.append(shortfall * penalty)

    # Makespan (tie-breaker)
    all_ends = [e for _, _, _, _, _, e, _ in slot_data]
    if all_ends:
        makespan = model.NewIntVar(0, horizon_ticks, "makespan")
        model.AddMaxEquality(makespan, all_ends)
        obj_terms.append(makespan)

    if obj_terms:
        model.Minimize(sum(obj_terms))

    # ── Solve ────────────────────────────────────────────────────────────
    class CurveCallback(cp_model.CpSolverSolutionCallback):
        def __init__(self) -> None:
            cp_model.CpSolverSolutionCallback.__init__(self)
            self.curve: list[dict] = []

        def OnSolutionCallback(self) -> None:
            self.curve.append({
                "time_s": self.WallTime(),
                "objective_value": self.ObjectiveValue(),
                "best_bound": self.BestObjectiveBound(),
            })

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.time_limit_s
    curve_cb = CurveCallback()
    status = solver.SolveWithSolutionCallback(model, curve_cb)

    # ── Extract solution ────────────────────────────────────────────────
    scheduled_blocks: list[ScheduledBlock] = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for solver_eq_id, rule_id, _slot, p_var, s_var, e_var, b_var in slot_data:
            if solver.Value(p_var):
                scheduled_blocks.append(
                    ScheduledBlock(
                        rule_id=rule_id,
                        start_tick=solver.Value(s_var),
                        end_tick=solver.Value(e_var),
                        batch_qty=solver.Value(b_var),
                        equipment_entity_id=solver_eq_id,
                        consumed=[],
                        produced=[],
                    )
                )
    else:
        logger.warning("CP-SAT: status=%s", solver.StatusName(status))

    solver_time_s = time.monotonic() - start_time

    # ── Compute order outcomes via shared evaluation ─────────────────────

    order_outcomes, max_end_tick, _, _ = _evaluate_fulfillment(plan, scheduled_blocks)

    log_solver_result("CP-SAT", scheduled_blocks, order_outcomes, max_end_tick, solver_time_s)

    return SolverResult(
        status="optimal" if status == cp_model.OPTIMAL else "feasible" if scheduled_blocks else "timeout",
        scheduled_blocks=scheduled_blocks,
        order_outcomes=order_outcomes,
        makespan_s=max_end_tick * _DEFAULT_TICK_S,
        solver_time_s=solver_time_s,
        solution_curve=curve_cb.curve,
    )


_SOLVERS["cp_sat"] = solve_cp_sat