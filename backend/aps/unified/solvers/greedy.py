"""Greedy solver — interleaved BOM-order list scheduling.

Registered as the ``"greedy"`` solver plugin.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from aps.unified._compile import (
    CompiledEntity,
    CompiledRule,
    CompiledSelector,
)
from aps.unified._evaluate import (
    _DEFAULT_TICK_S,
    _get_expiry_tick,
    evaluate_fulfillment as _evaluate_fulfillment,
    log_solver_result,
)
from aps.unified._types import (
    EntitySnapshot,
    OrderOutcome,
    ScheduledBlock,
    SolverResult,
)
from aps.unified.solvers import _SOLVERS  # direct registry access (avoids circular import via decorator)

if TYPE_CHECKING:

    from aps.unified._compile import CompiledPlan
    from aps.unified.solvers import SolverConfig

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────


def _deep_copy_inventory(
    inventory: dict[str, list[CompiledEntity]] | Mapping[str, Sequence[CompiledEntity]],
) -> dict[str, list[CompiledEntity]]:
    return {k: list(v) for k, v in inventory.items()}


def _match_entity(
    pool: list[CompiledEntity],
    selector: CompiledSelector,
) -> list[CompiledEntity]:
    """Find entities matching the selector conditions."""
    return [
        e for e in pool
        if all(e.fields.get(key) == val for key, val in selector.conditions.items())
    ]


def _is_expired_at(entity: CompiledEntity, tick: int) -> bool:
    """Check if an entity has expired by the given tick."""
    expiry_tick = _get_expiry_tick(entity)
    return expiry_tick is not None and expiry_tick < tick


def _consume_entities(
    inventory: dict[str, list[CompiledEntity]],
    selector: CompiledSelector,
    count: int,
    current_tick: int | None = None,
) -> list[CompiledEntity]:
    """Consume ``count`` entities matching the selector from inventory.

    If *current_tick* is given, expired entities are skipped
    (entities with expiry < current_tick are not consumed).
    """
    entity_type: str | object = selector.conditions.get("type", "")
    if not isinstance(entity_type, str):
        return []

    pool = inventory.get(entity_type, [])
    matches = _match_entity(pool, selector)
    if current_tick is not None:
        # Filter out expired entities, prefer non-expired
        valid = [e for e in matches if not _is_expired_at(e, current_tick)]
        taken = valid[: min(count, len(valid))]
    else:
        taken = matches[: min(count, len(matches))]
    for entity in taken:
        pool.remove(entity)
    if pool:
        inventory[entity_type] = pool
    elif entity_type in inventory:
        del inventory[entity_type]
    return taken


def _produce_entities(
    inventory: dict[str, list[CompiledEntity]],
    selector: CompiledSelector,
    count: int,
    entity_counter: list[int],
) -> list[CompiledEntity]:
    """Produce ``count`` entities matching the selector."""
    entity_type: str | object = selector.conditions.get("type", "")
    if not isinstance(entity_type, str):
        entity_type = "unknown"

    produced: list[CompiledEntity] = []
    for _ in range(count):
        entity_counter[0] += 1
        produced.append(
            CompiledEntity(
                entity_id=f"p{entity_counter[0]:04d}",
                fields=dict(selector.conditions),
                signature=entity_type,
            )
        )
    inventory.setdefault(entity_type, []).extend(produced)
    return produced


def _inventory_count(
    inventory: dict[str, list[CompiledEntity]],
    selector: CompiledSelector,
) -> int:
    """Count entities matching *selector* in *inventory*."""
    etype = selector.conditions.get("type")
    if not isinstance(etype, str) or etype not in inventory:
        return 0
    return len(_match_entity(inventory[etype], selector))


def _available_batch_size(
    rule: CompiledRule,
    inventory: dict[str, list[CompiledEntity]],
    current_tick: int | None = None,
) -> int:
    """Maximum batch size for a rule given available materials, capped by batch_max.

    Checks both ``consume`` (per batch qty) and ``consume_batch`` (per run).
    If *current_tick* is given, expired entities are excluded.
    """
    max_batch = rule.batch_max
    for _, sel in rule.consume:
        cons_type = sel.conditions.get("type")
        if isinstance(cons_type, str):
            pool = inventory.get(cons_type)
            if not pool:
                return 0
            matches = _match_entity(pool, sel)
            if current_tick is not None:
                matches = [e for e in matches if not _is_expired_at(e, current_tick)]
            if not matches:
                return 0
            max_batch = min(max_batch, len(matches))
    for _, sel in rule.consume_batch:
        cons_type = sel.conditions.get("type")
        if isinstance(cons_type, str):
            pool = inventory.get(cons_type)
            if not pool:
                return 0
            matches = _match_entity(pool, sel)
            if current_tick is not None:
                matches = [e for e in matches if not _is_expired_at(e, current_tick)]
            if not matches:
                return 0
    return max(0, max_batch)


def _holding_rule_max_qty(
    inventory: dict[str, list[CompiledEntity]],
    plan: CompiledPlan,
    produce_type: str,
    desired_qty: int,
) -> int:
    """Return the max qty of *produce_type* that can be produced without exceeding holding rule max.

    For each holding rule matching *produce_type*, computes how many more
    units can be added before hitting ``max``. Returns the minimum across
    all matching rules, or *desired_qty* if no rule limits it.
    """
    for hr in plan.holding_rules:
        hr_type = hr.selector.conditions.get("type")
        if hr_type == produce_type and hr.max is not None:
            from aps.unified._evaluate import _inventory_count
            current = _inventory_count(inventory, hr.selector)
            max_allowed = int(hr.max)
            if current >= max_allowed:
                return 0  # already at max, can't produce more
            return min(desired_qty, max_allowed - current)
    return desired_qty


# ── Bottleneck-aware rule ordering ─────────────────────────────────────────


def _compute_rule_order(rules: list[CompiledRule]) -> list[CompiledRule]:
    """Return rules ordered by topological depth, then most-blocking first."""
    rule_map = {r.rule_id: r for r in rules}

    produces: dict[str, set[str]] = {}
    consumes: dict[str, set[str]] = {}
    for r in rules:
        produces[r.rule_id] = set()
        for _, cs in r.produce:
            t = cs.conditions.get("type")
            if isinstance(t, str):
                produces[r.rule_id].add(t)
        consumes[r.rule_id] = set()
        for _, cs in r.consume:
            t = cs.conditions.get("type")
            if isinstance(t, str):
                consumes[r.rule_id].add(t)

    adj: dict[str, list[str]] = {r.rule_id: [] for r in rules}
    type_to_producer: dict[str, str] = {}
    for r in rules:
        for t in produces[r.rule_id]:
            type_to_producer[t] = r.rule_id

    in_degree: dict[str, int] = {r.rule_id: 0 for r in rules}
    for r in rules:
        for t in consumes[r.rule_id]:
            producer = type_to_producer.get(t)
            if producer and producer != r.rule_id:
                adj.setdefault(producer, []).append(r.rule_id)
                in_degree[r.rule_id] = in_degree.get(r.rule_id, 0) + 1

    blocked_count: dict[str, int] = {}
    for r_id in in_degree:
        blocked_count[r_id] = len(adj.get(r_id, []))

    queue = sorted(
        [r_id for r_id, deg in in_degree.items() if deg == 0],
        key=lambda r_id: -blocked_count.get(r_id, 0),
    )
    sorted_ids: list[str] = []

    while queue:
        r_id = queue.pop(0)
        sorted_ids.append(r_id)
        for neighbor in adj.get(r_id, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
                queue.sort(key=lambda r: -blocked_count.get(r, 0))

    remaining = [r.rule_id for r in rules if r.rule_id not in sorted_ids]
    sorted_ids.extend(remaining)

    return [rule_map[r_id] for r_id in sorted_ids]


# ── Batch scheduling ───────────────────────────────────────────────────────


def _try_schedule_batch(
    rule: CompiledRule,
    inventory: dict[str, list[CompiledEntity]],
    equipment_available: dict[str, int],
    entity_counter: list[int],
    horizon_ticks: int,
    scheduled_blocks: list[ScheduledBlock],
    plan: CompiledPlan | None = None,
) -> tuple[int, int] | None:
    """Try to schedule one batch of *rule*.  Appends to *scheduled_blocks* on success.

    If *plan* is provided, holding rule max constraints are enforced on produce types.
    """
    # Late import to break circular dependency

    # Collect all matching equipment entities for this rule
    equipment_pool: list[CompiledEntity] = []
    for _, eq_sel in rule.consume_batch:
        eq_type = eq_sel.conditions.get("type")
        if isinstance(eq_type, str) and eq_type in inventory:
            equipment_pool.extend(_match_entity(inventory[eq_type], eq_sel))
    if not equipment_pool:
        return None

    # Pick the least-loaded equipment
    eq = min(equipment_pool, key=lambda e: equipment_available.get(e.entity_id, 0))
    eq_start = equipment_available.get(eq.entity_id, 0)

    if eq_start >= horizon_ticks:
        return None

    # Determine batch size, respecting expiry
    max_batch = rule.batch_max
    for _, sel in rule.consume:
        cons_type = sel.conditions.get("type")
        if isinstance(cons_type, str):
            pool = inventory.get(cons_type)
            if not pool:
                return None
            # Filter out expired entities (expiry < eq_start)
            valid_pool = [
                e for e in _match_entity(pool, sel)
                if not _is_expired_at(e, eq_start)
            ]
            if not valid_pool:
                return None
            max_batch = min(max_batch, len(valid_pool))

    # Check holding rule max for produce types (reduce batch if needed)
    if plan is not None:
        for _, sel in rule.produce:
            prod_type = sel.conditions.get("type")
            if isinstance(prod_type, str):
                qty_per_batch = int(sel.num)
                max_from_holding = _holding_rule_max_qty(inventory, plan, prod_type, max_batch * qty_per_batch)
                max_batch = min(max_batch, max_from_holding // qty_per_batch)

    batch_qty = max_batch
    if batch_qty < rule.batch_min:
        return None

    duration = rule.duration_batch_ticks + batch_qty * rule.duration_ticks
    eq_end = eq_start + duration

    if eq_end > horizon_ticks:
        max_fit = (horizon_ticks - eq_start - rule.duration_batch_ticks) // max(1, rule.duration_ticks)
        batch_qty = min(batch_qty, max_fit)
        if batch_qty < rule.batch_min:
            return None
        duration = rule.duration_batch_ticks + batch_qty * rule.duration_ticks
        eq_end = eq_start + duration

    # Consume (prefer non-expired entities)
    consumed_snapshots: list[EntitySnapshot] = []
    for _, sel in rule.consume:
        taken = _consume_entities(inventory, sel, batch_qty, eq_start)
        for t in taken:
            consumed_snapshots.append(
                EntitySnapshot(entity_type=t.signature, num=1.0, fields=dict(t.fields))
            )
    for _, sel in rule.consume_batch:
        taken = _consume_entities(inventory, sel, 1, eq_start)
        for t in taken:
            consumed_snapshots.append(
                EntitySnapshot(entity_type=t.signature, num=1.0, fields=dict(t.fields))
            )

    # Produce
    produced_snapshots: list[EntitySnapshot] = []
    for _, sel in rule.produce:
        produced = _produce_entities(inventory, sel, batch_qty, entity_counter)
        for p in produced:
            produced_snapshots.append(
                EntitySnapshot(entity_type=p.signature, num=1.0, fields=dict(p.fields))
            )

    produced_equipment_ids: list[str] = []
    for _, sel in rule.produce_batch:
        produced = _produce_entities(inventory, sel, 1, entity_counter)
        for p in produced:
            produced_snapshots.append(
                EntitySnapshot(entity_type=p.signature, num=1.0, fields=dict(p.fields))
            )
            produced_equipment_ids.append(p.entity_id)

    equipment_available[eq.entity_id] = eq_end
    for new_id in produced_equipment_ids:
        equipment_available[new_id] = eq_end

    scheduled_blocks.append(
        ScheduledBlock(
            rule_id=rule.rule_id,
            start_tick=eq_start,
            end_tick=eq_end,
            batch_qty=batch_qty,
            equipment_entity_id=eq.entity_id,
            consumed=consumed_snapshots,
            produced=produced_snapshots,
        )
    )

    return eq_end, batch_qty


# ── Solver entry point ─────────────────────────────────────────────────────


def solve_greedy(
    plan: CompiledPlan,
    config: SolverConfig,
) -> SolverResult:
    """Greedy solver — interleaved BOM-order list scheduling.

    Registered as the ``"greedy"`` solver plugin.

    Parameters
    ----------
    plan :
        The compiled planning problem.
    config :
        Solver configuration (uses ``horizon_ticks``, ignores others).

    Returns
    -------
    SolverResult with scheduled blocks and order outcomes (always feasible).
    """
    start_time = time.monotonic()
    inventory = _deep_copy_inventory(plan.initial_entities)
    equipment_available: dict[str, int] = {}
    entity_counter = [sum(len(v) for v in plan.initial_entities.values())]
    scheduled_blocks: list = []
    horizon_ticks = config.horizon_ticks or plan.horizon_ticks

    # BOM order
    bom_order = _compute_rule_order(list(plan.rules))

    # Phase 1: Demand-driven push — compute order demand, work backwards
    # to set batch targets for each rule in the BOM chain.
    order_demand: dict[str, float] = {}
    # Track order priority: type -> max penalty among orders demanding it
    order_priority: dict[str, float] = {}
    for order in plan.orders:
        penalty = max(order.late_delivery_penalty_per_s * _DEFAULT_TICK_S, 1.0)
        for _, sel in order.consume:
            t = sel.conditions.get("type")
            if isinstance(t, str):
                order_demand[t] = order_demand.get(t, 0) + sel.num
                order_priority[t] = max(order_priority.get(t, 0), penalty)

    # Add holding rule consumption to demand.
    # Holding rules with consume + duration_s consume entities over time.
    # Estimate total consumption over the horizon as:
    #   count * num * (horizon_s / duration_s)
    for hr in plan.holding_rules:
        if hr.consume is None or hr.duration_s is None or hr.duration_s <= 0:
            continue
        hr_type = hr.selector.conditions.get("type")
        if not isinstance(hr_type, str):
            continue
        # Count initial entities matching this holding rule
        initial_count = 0
        for t, ents in plan.initial_entities.items():
            if t == hr_type:
                for e in ents:
                    if all(e.fields.get(k) == v for k, v in hr.selector.conditions.items() if k != "type"):
                        initial_count += 1
        if initial_count <= 0:
            continue
        horizon_s = horizon_ticks * _DEFAULT_TICK_S  # approximate
        for _, sel in hr.consume:
            cons_type = sel.conditions.get("type")
            if isinstance(cons_type, str):
                total_consumption = initial_count * sel.num * (horizon_s / hr.duration_s)
                order_demand[cons_type] = order_demand.get(cons_type, 0) + total_consumption

    # BOM-demand: for each rule, compute the total demand it must satisfy
    # (sum of order demand for its output types, divided by its output rate)
    rule_targets: dict[str, float] = {}
    rule_priority: dict[str, float] = {}  # higher = more urgent
    for r in bom_order:
        max_priority = 1.0
        for _, sel in r.produce:
            t = sel.conditions.get("type")
            if isinstance(t, str) and t in order_demand:
                target = order_demand[t]
                rule_targets[r.rule_id] = max(rule_targets.get(r.rule_id, 0), target)
                max_priority = max(max_priority, order_priority.get(t, 1.0))
        rule_priority[r.rule_id] = max_priority

    for _ in range(5000):
        progress = False
        # Sort rules by priority (high-penalty orders first) within BOM order
        for rule in sorted(bom_order, key=lambda r: -rule_priority.get(r.rule_id, 1.0)):
            target = rule_targets.get(rule.rule_id, 1)
            # Scale batch aggressiveness to demand: larger demand = more per pass
            aggressiveness = max(10, min(50, int(target / rule.batch_max) + 1))
            for _ in range(aggressiveness):
                avail = _available_batch_size(rule, inventory)
                if avail < rule.batch_min:
                    break
                result = _try_schedule_batch(
                    rule, inventory, equipment_available,
                    entity_counter, horizon_ticks, scheduled_blocks,
                    plan,
                )
                if result is None:
                    break
                progress = True

        if not progress:
            break

    # Evaluate order fulfillment using shared evaluation toolkit

    order_outcomes, max_end_tick, expiry_violations, holding_violations = _evaluate_fulfillment(
        plan, scheduled_blocks
    )

    if expiry_violations:
        logger.warning("Greedy: %d expiry violations", len(expiry_violations))
    if holding_violations:
        logger.warning("Greedy: %d holding rule violations", len(holding_violations))

    solver_time_s = time.monotonic() - start_time

    log_solver_result("Greedy", scheduled_blocks, order_outcomes, max_end_tick, solver_time_s)

    return SolverResult(
        status="feasible",
        scheduled_blocks=scheduled_blocks,
        order_outcomes=order_outcomes,
        makespan_s=max_end_tick * _DEFAULT_TICK_S,
        solver_time_s=solver_time_s,
    )


# Register this solver plugin
_SOLVERS["greedy"] = solve_greedy
