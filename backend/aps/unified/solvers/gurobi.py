"""Gurobi MIP solver — batch scheduling with shortfall minimization.

Registered as the ``"gurobi"`` solver plugin.

Uses indicator constraints for active/inactive logic and big-M for
equipment no-overlap constraints.  Objective matches CP-SAT: minimize
weighted shortfall + makespan term.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import gurobipy as gp
from gurobipy import GRB

from aps.unified.solvers import _SOLVERS

if TYPE_CHECKING:

    from aps.unified._compile import CompiledPlan, CompiledRule
    from aps.unified._types import (
    EntitySnapshot,
    OrderOutcome,
    ScheduledBlock,
    SolverResult,
)
    from aps.unified.solvers import SolverConfig

logger = logging.getLogger(__name__)

# Free Gurobi license limits model size.  Adjust slots based on problem scale.
# With a commercial license, increase to 10+ for better solutions.
# Free Gurobi license limits model size (~2000 vars). Reduce slots accordingly.
# Commercial license: increase to 10+.
MAX_SLOTS = 2


def solve_gurobi(
    plan: CompiledPlan,
    config: SolverConfig,
) -> SolverResult:
    """Solve with Gurobi MIP."""
    start_time = time.monotonic()
    horizon = config.horizon_ticks or plan.horizon_ticks

    model = gp.Model("aps_gurobi")
    model.setParam("OutputFlag", 0)
    model.setParam("TimeLimit", max(1.0, config.time_limit_s))
    model.setParam("MIPFocus", 1)  # focus on feasible solutions
    model.setParam("Threads", 4)

    # ── Build equipment → rule mapping ──────────────────────────────────
    equip_rules: dict[str, list[CompiledRule]] = {}
    for r in plan.rules:
        for _, sel in r.consume_batch:
            etype = sel.conditions.get("type")
            if isinstance(etype, str):
                pool = plan.initial_entities.get(etype, [])
                for ent in pool:
                    equip_rules.setdefault(ent.entity_id, []).append(r)

    if not equip_rules:
        logger.warning("Gurobi: no equipment found, returning empty solution")
        return SolverResult(
            status="feasible",
            scheduled_blocks=[],
            order_outcomes=[],
            makespan_s=0,
            solver_time_s=time.monotonic() - start_time,
        )

    # ── Slot variables ──────────────────────────────────────────────────
    # For each (equipment, rule) pair, create MAX_SLOTS potential slots.
    # active[e][r][s] = binary, batch[e][r][s] = integer 0..batch_max
    # start[e][r][s] = integer 0..horizon, end[e][r][s] = integer 0..horizon
    active: dict[str, dict[str, list]] = {}
    batch: dict[str, dict[str, list]] = {}
    start: dict[str, dict[str, list]] = {}
    end: dict[str, dict[str, list]] = {}

    for eq_id, rules in equip_rules.items():
        active[eq_id] = {}
        batch[eq_id] = {}
        start[eq_id] = {}
        end[eq_id] = {}
        for r in rules:
            active[eq_id][r.rule_id] = []
            batch[eq_id][r.rule_id] = []
            start[eq_id][r.rule_id] = []
            end[eq_id][r.rule_id] = []
            max_dur = r.duration_batch_ticks + r.batch_max * r.duration_ticks
            for s in range(MAX_SLOTS):
                aname = f"a_{eq_id}_{r.rule_id}_s{s}"
                av = model.addVar(vtype=GRB.BINARY, name=aname)
                bname = f"b_{eq_id}_{r.rule_id}_s{s}"
                bv = model.addVar(lb=0, ub=r.batch_max, vtype=GRB.INTEGER, name=bname)
                sv = model.addVar(lb=0, ub=horizon, vtype=GRB.INTEGER, name=f"s_{eq_id}_{r.rule_id}_s{s}")
                ev = model.addVar(lb=0, ub=horizon, vtype=GRB.INTEGER, name=f"e_{eq_id}_{r.rule_id}_s{s}")
                active[eq_id][r.rule_id].append(av)
                batch[eq_id][r.rule_id].append(bv)
                start[eq_id][r.rule_id].append(sv)
                end[eq_id][r.rule_id].append(ev)

                # Duration: end = start + duration_batch + batch * duration_unit
                dur = model.addVar(lb=0, ub=max_dur, vtype=GRB.INTEGER, name=f"d_{eq_id}_{r.rule_id}_s{s}")
                model.addConstr(dur == r.duration_batch_ticks + bv * r.duration_ticks)

                # When active: end == start + dur. When inactive: end == start, batch == 0.
                model.addConstr((av == 1) >> (ev == sv + dur))
                model.addConstr((av == 0) >> (ev == sv))
                model.addConstr((av == 1) >> (bv >= r.batch_min))
                model.addConstr((av == 0) >> (bv == 0))

                # Symmetry breaking: order slots by start time
                if s > 0:
                    prev_s = start[eq_id][r.rule_id][s - 1]
                    model.addConstr(sv >= prev_s)

    # ── No-overlap constraints (big-M) ──────────────────────────────────
    big_m = horizon
    for eq_id, rules in equip_rules.items():
        # Collect all slot (start, end, active) tuples for this equipment
        all_slots: list[tuple] = []
        for r in rules:
            for s in range(MAX_SLOTS):
                all_slots.append((
                    start[eq_id][r.rule_id][s],
                    end[eq_id][r.rule_id][s],
                    active[eq_id][r.rule_id][s],
                ))

        for i in range(len(all_slots)):
            s_i, e_i, a_i = all_slots[i]
            for j in range(i + 1, len(all_slots)):
                s_j, e_j, a_j = all_slots[j]
                # y = 1 means i before j, y = 0 means j before i
                y = model.addVar(vtype=GRB.BINARY, name=f"seq_{eq_id}_{i}_{j}")
                # If both active, enforce ordering via big_m:
                model.addConstr(e_i <= s_j +big_m* (3 - a_i - a_j - y))
                model.addConstr(e_j <= s_i +big_m* (2 - a_i - a_j + y))

    # ── Material constraints ────────────────────────────────────────────
    initial_counts: dict[str, int] = {
        t: len(ents) for t, ents in plan.initial_entities.items()
    }

    # Collect per-type batch variable contributions
    type_terms_prod: dict[str, list] = {}
    type_terms_cons: dict[str, list] = {}
    for eq_id, rules in equip_rules.items():
        for r in rules:
            for s in range(MAX_SLOTS):
                bv = batch[eq_id][r.rule_id][s]
                for _, sel in r.produce:
                    t = sel.conditions.get("type")
                    if isinstance(t, str):
                        type_terms_prod.setdefault(t, []).append(bv)
                for _, sel in r.consume:
                    t = sel.conditions.get("type")
                    if isinstance(t, str):
                        type_terms_cons.setdefault(t, []).append((-1, bv))

    for t in type_terms_prod:
        init = initial_counts.get(t, 0)
        if t in type_terms_cons:
            # init + sum(produce) + sum(-1 * consume) >= 0
            prod_sum = gp.quicksum(type_terms_prod[t])
            cons_sum = gp.quicksum(b for _, b in type_terms_cons[t])
            model.addConstr(init + prod_sum - cons_sum >= 0)
        else:
            prod_sum = gp.quicksum(type_terms_prod[t])
            model.addConstr(init + prod_sum >= 0)
    for t in type_terms_cons:
        if t not in type_terms_prod:
            cons_sum = gp.quicksum(b for _, b in type_terms_cons[t])
            init = initial_counts.get(t, 0)
            model.addConstr(init - cons_sum >= 0)

    # ── Objective: shortfall penalties + makespan ───────────────────────
    obj_terms: list = []

    for order in plan.orders:
        for _, sel in order.consume:
            t = sel.conditions.get("type")
            if not isinstance(t, str):
                continue
            needed = int(sel.num)
            init = initial_counts.get(t, 0)
            prod_terms = type_terms_prod.get(t, [])
            cons_terms = [b for _, b in type_terms_cons.get(t, [])]

            avail = init + gp.quicksum(prod_terms) - gp.quicksum(cons_terms)

            # Shortfall = max(0, needed - avail)
            shortfall = model.addVar(lb=0, ub=needed, vtype=GRB.INTEGER, name=f"short_{order.order_id}")
            model.addConstr(shortfall >= needed - avail)

            penalty = int(order.late_delivery_penalty_per_s * 60) if order.late_delivery_penalty_per_s else 100
            if penalty < 1:
                penalty = 100
            obj_terms.append(shortfall * penalty)

    # Makespan (tie-breaker)
    all_ends: list = []
    for eq_id, rules in equip_rules.items():
        for r in rules:
            all_ends.extend(end[eq_id][r.rule_id])
    if all_ends:
        makespan = model.addVar(lb=0, ub=horizon, vtype=GRB.INTEGER, name="makespan")
        model.addConstr(makespan == gp.max_(all_ends))
        obj_terms.append(makespan)  # small weight, just tie-breaking

    if obj_terms:
        model.setObjective(gp.quicksum(obj_terms), GRB.MINIMIZE)

    # ── Solution callback for decay curve ──────────────────────────────
    curve_data: list[dict] = []

    def _mip_cb(model: gp.Model, where: int) -> None:
        if where == GRB.Callback.MIPSOL:
            obj = model.cbGet(GRB.Callback.MIPSOL_OBJ)
            runtime = model.cbGet(GRB.Callback.RUNTIME)
            curve_data.append({
                "time_s": runtime,
                "objective_value": obj,
                "best_bound": model.cbGet(GRB.Callback.MIPSOL_OBJBND),
            })

    model.Params.LazyConstraints = 1  # required when using callbacks

    # ── Solve ───────────────────────────────────────────────────────────
    model.optimize(_mip_cb)

    solver_time_s = time.monotonic() - start_time

    # ── Extract solution ────────────────────────────────────────────────
    scheduled_blocks: list[ScheduledBlock] = []
    status_str = "timeout"

    if model.Status in (GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SUBOPTIMAL):
        if model.SolCount > 0:
            status_str = "optimal" if model.Status == GRB.OPTIMAL else "feasible"
            for eq_id, rules in equip_rules.items():
                for r in rules:
                    for s in range(MAX_SLOTS):
                        if active[eq_id][r.rule_id][s].X > 0.5:
                            bv = round(batch[eq_id][r.rule_id][s].X)
                            sv = round(start[eq_id][r.rule_id][s].X)
                            ev = round(end[eq_id][r.rule_id][s].X)
                            if bv > 0:
                                scheduled_blocks.append(
                                    ScheduledBlock(
                                        rule_id=r.rule_id,
                                        start_tick=sv,
                                        end_tick=ev,
                                        batch_qty=bv,
                                        equipment_entity_id=eq_id,
                                        consumed=[],
                                        produced=[],
                                    )
                                )
    elif model.Status == GRB.INFEASIBLE:
        logger.warning("Gurobi: model infeasible")
    else:
        logger.warning("Gurobi: status=%s", model.Status)

    # ── Compute order outcomes via shared evaluation ────────────────────
    from aps.unified._evaluate import evaluate_fulfillment
    order_outcomes, max_end_tick, _, _ = evaluate_fulfillment(plan, scheduled_blocks)

    logger.info(
        "Gurobi: %d blocks, %d/%d orders, %ds makespan, %.2fs",
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
        solution_curve=curve_data,
    )


_SOLVERS["gurobi"] = solve_gurobi
