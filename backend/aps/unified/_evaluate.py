"""Shared evaluation toolkit — inventory simulation, expiry, holding rules, objective.

All solvers use this module for:
1. Tick-by-tick inventory simulation with expiry handling
2. Order fulfillment checking (release tick, deadline, holding rules)
3. Objective expression evaluation

This is the single source of truth for constraint checking.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from aps.unified._compile import (
    CompiledEntity,
    CompiledHoldingRule,
    CompiledOrder,
    CompiledPlan,
    CompiledRule,
    CompiledSelector,
)
from aps.unified._expr import compile_expr
from aps.unified._types import EvaluationResult

if TYPE_CHECKING:

    from aps.unified._types import OrderOutcome, ScheduledBlock

logger = logging.getLogger(__name__)

_DEFAULT_TICK_S = 60  # 1-minute ticks


# ── Helpers ──────────────────────────────────────────────────────────────────


def _match_entity(
    pool: list[CompiledEntity],
    selector: CompiledSelector,
) -> list[CompiledEntity]:
    """Find entities matching the selector conditions."""
    return [
        e for e in pool
        if all(e.fields.get(key) == val for key, val in selector.conditions.items())
    ]


def _consume_entities(
    inventory: dict[str, list[CompiledEntity]],
    selector: CompiledSelector,
    count: int,
) -> list[CompiledEntity]:
    """Consume ``count`` entities matching the selector from inventory."""
    entity_type: str | object = selector.conditions.get("type", "")
    if not isinstance(entity_type, str):
        return []

    pool = inventory.get(entity_type, [])
    matches = _match_entity(pool, selector)
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


# ── Expiry handling ──────────────────────────────────────────────────────────


def _tick_for_datetime(dt: object, tick_s: int = _DEFAULT_TICK_S) -> int | None:
    """Convert a datetime field value to a tick offset.

    If *dt* is a datetime, returns the tick (assuming the value is
    an absolute datetime — we compare relative to the epoch for sorting).
    If *dt* is already numeric, return it as-is.
    If *dt* is None or not convertible, return None.
    """
    if isinstance(dt, datetime):
        # Use the datetime's own timestamp for comparison
        epoch = datetime(2026, 1, 1, tzinfo=UTC)
        delta_s = (dt - epoch).total_seconds()
        return max(0, int(delta_s / tick_s))
    if isinstance(dt, (int, float)):
        return int(dt)
    return None


def _get_expiry_tick(entity: CompiledEntity, tick_s: int = _DEFAULT_TICK_S) -> int | None:
    """Get the expiry tick for an entity, or None if it doesn't expire."""
    expiry_val = entity.fields.get("expiry")
    if expiry_val is None:
        return None
    return _tick_for_datetime(expiry_val, tick_s)


def _remove_expired_entities(
    inventory: dict[str, list[CompiledEntity]],
    current_tick: int,
    tick_s: int = _DEFAULT_TICK_S,
) -> dict[str, list[CompiledEntity]]:
    """Remove entities that have expired by *current_tick*.

    Returns a new inventory dict with expired entities removed.
    An entity expires when its expiry tick < current_tick.
    """
    new_inv: dict[str, list[CompiledEntity]] = {}
    for etype, entities in inventory.items():
        surviving: list[CompiledEntity] = []
        for e in entities:
            expiry_tick = _get_expiry_tick(e, tick_s)
            if expiry_tick is not None and expiry_tick < current_tick:
                continue  # expired, skip
            surviving.append(e)
        if surviving:
            new_inv[etype] = surviving
    return new_inv


# ── Holding rule checking ────────────────────────────────────────────────────


def _check_holding_rules(
    plan: CompiledPlan,
    inventory: dict[str, list[CompiledEntity]],
) -> tuple[list[str], int]:
    """Check holding rules against current inventory.

    Returns (violations, total_excess).

    A violation occurs when:
    - A holding rule has ``max`` and inventory exceeds it
    """
    violations: list[str] = []
    total_excess = 0

    for hr in plan.holding_rules:
        hr_type = hr.selector.conditions.get("type")
        if not isinstance(hr_type, str):
            continue

        count = _inventory_count(inventory, hr.selector)
        if hr.max is not None and count > hr.max:
            excess = int(count - hr.max)
            total_excess += excess
            violations.append(
                f"holding rule for {hr_type!r}: {count} > max {hr.max} (excess {excess})"
            )

    return violations, total_excess


def _apply_holding_consumption(
    plan: CompiledPlan,
    inventory: dict[str, list[CompiledEntity]],
    current_tick: int,
    tick_s: int = _DEFAULT_TICK_S,
) -> list[str]:
    """Apply ongoing consumption from holding rules at *current_tick*.

    For each holding rule with ``consume`` + ``duration_s``:
      rate = sum(consume.num) * tick_s / duration_s  per held entity
      If the entity type matching the selector is in inventory, consume
      the required entities.

    Returns a list of consumption events (for logging/debugging).
    """
    events: list[str] = []

    for hr in plan.holding_rules:
        if hr.consume is None or hr.duration_s is None or hr.duration_s <= 0:
            continue

        # Count entities matching the selector
        count = float(_inventory_count(inventory, hr.selector))
        if count <= 0:
            continue

        # For each matching entity, consume at rate per tick
        for _, sel in hr.consume:
            cons_type = sel.conditions.get("type")
            if not isinstance(cons_type, str):
                continue

            # Total consumption = count * num * (tick_s / duration_s)
            rate = count * sel.num * (tick_s / hr.duration_s)
            to_consume = max(1, int(round(rate)))

            available = _inventory_count(inventory, sel)
            if available > 0:
                taken = _consume_entities(inventory, sel, min(to_consume, available))
                if taken:
                    events.append(
                        f"tick={current_tick} holding_rule for {hr.selector.conditions.get('type', '?')}: "
                        f"consumed {len(taken)}x {cons_type} (rate={rate:.2f}/tick)"
                    )

    return events


# ── Tick-by-tick inventory simulation ────────────────────────────────────────


def simulate_inventory(
    plan: CompiledPlan,
    blocks: Sequence[ScheduledBlock],
    tick_s: int = _DEFAULT_TICK_S,
) -> dict[int, dict[str, list[CompiledEntity]]]:
    """Simulate inventory tick by tick over the planning horizon.

    Processes blocks in order of start_tick, applying:
    1. Expiry removal at each tick boundary
    2. Consume/produce per block
    3. Holding rule constraint checking

    Returns a dict mapping tick → inventory snapshot (for analysis).
    This is the authoritative inventory simulation used by all evaluators.
    """
    # Initialize inventory
    inventory: dict[str, list[CompiledEntity]] = {
        t: list(ents) for t, ents in plan.initial_entities.items()
    }
    entity_counter = [sum(len(v) for v in plan.initial_entities.values())]

    # Sort blocks by start tick
    sorted_blocks = sorted(blocks, key=lambda b: b.start_tick)

    max_tick = max((b.end_tick for b in blocks), default=0)
    snapshots: dict[int, dict[str, list[CompiledEntity]]] = {}

    current_tick = 0
    block_idx = 0

    while current_tick <= max_tick:
        # Remove expired entities at this tick boundary
        inventory = _remove_expired_entities(inventory, current_tick, tick_s)

        # Process all blocks starting at this tick
        while block_idx < len(sorted_blocks) and sorted_blocks[block_idx].start_tick == current_tick:
            b = sorted_blocks[block_idx]
            rule = next((r for r in plan.rules if r.rule_id == b.rule_id), None)
            if rule is not None:
                # Consume per-unit
                for _, sel in rule.consume:
                    _consume_entities(inventory, sel, b.batch_qty)
                # Consume per-batch
                for _, sel in rule.consume_batch:
                    _consume_entities(inventory, sel, 1)
                # Produce per-unit
                for _, sel in rule.produce:
                    _produce_entities(inventory, sel, b.batch_qty, entity_counter)
                # Produce per-batch
                for _, sel in rule.produce_batch:
                    _produce_entities(inventory, sel, 1, entity_counter)
            block_idx += 1

        # Apply holding rule consumption (ongoing consumption while held)
        _apply_holding_consumption(plan, inventory, current_tick, tick_s)

        # Snapshot
        snapshots[current_tick] = {
            t: list(ents) for t, ents in inventory.items()
        }

        current_tick += 1

    return snapshots


# ── Order fulfillment evaluation ─────────────────────────────────────────────


def evaluate_fulfillment(
    plan: CompiledPlan,
    blocks: Sequence[ScheduledBlock],
    tick_s: int = _DEFAULT_TICK_S,
) -> tuple[list[OrderOutcome], int, list[str], list[str]]:
    """Evaluate order fulfillment from scheduled blocks.

    This is the authoritative evaluation function used by all solvers.
    It checks:
    1. Order fulfillment (inventory at end of horizon)
    2. Release tick (orders not fulfilled before release)
    3. Holding rule violations
    4. Entity expiry violations

    Args:
        plan: The compiled planning problem.
        blocks: Scheduled blocks from a solver.
        tick_s: Tick duration in seconds.

    Returns:
        (order_outcomes, max_end_tick, expiry_violations, holding_violations)
    """
    from aps.unified._types import OrderOutcome

    # Run the authoritative inventory simulation
    snapshots = simulate_inventory(plan, blocks, tick_s)
    final_inventory = snapshots.get(max(snapshots.keys()), {}) if snapshots else {}

    max_end_tick = max((b.end_tick for b in blocks), default=0)

    # Check expiry violations: entities that were consumed after their expiry
    expiry_violations: list[str] = []
    for b in blocks:
        for consumed in b.consumed:
            # Check if any consumed entity had an expiry that was past
            expiry_val = consumed.fields.get("expiry")
            if expiry_val is not None:
                expiry_tick = _tick_for_datetime(expiry_val, tick_s)
                if expiry_tick is not None and expiry_tick < b.start_tick:
                    expiry_violations.append(
                        f"block {b.rule_id} at tick {b.start_tick} consumed "
                        f"entity {consumed.entity_type} that expired at tick {expiry_tick}"
                    )

    # Check holding rules
    holding_violations, _ = _check_holding_rules(plan, final_inventory)

    # Evaluate order fulfillment
    order_outcomes: list[OrderOutcome] = []
    for order in plan.orders:
        order_fulfilled = True
        completion_tick: int | None = None

        # Check release tick: orders fulfilled before release are not fulfilled
        earliest_fulfill_tick = 0
        if order.release_tick is not None:
            earliest_fulfill_tick = order.release_tick

        # Find the latest block that contributes to this order
        for b in blocks:
            for produced in b.produced:
                for _, sel in order.consume:
                    if produced.entity_type == sel.conditions.get("type"):
                        if b.start_tick >= earliest_fulfill_tick:
                            if completion_tick is None or b.end_tick > completion_tick:
                                completion_tick = b.end_tick

        # Check if order demand is fulfilled in final inventory
        for _, sel in order.consume:
            available = float(_inventory_count(final_inventory, sel))
            if available < sel.num:
                order_fulfilled = False
                break

        # If completion_tick is before release_tick, order is not fulfilled
        if completion_tick is not None and order.release_tick is not None:
            if completion_tick < order.release_tick:
                # Order was fulfilled before release — not valid
                # But if it's still available after release, it's fine
                # Check if there's enough inventory AFTER release_tick
                all_available = True
                for _, sel in order.consume:
                    available = float(_inventory_count(final_inventory, sel))
                    if available < sel.num:
                        all_available = False
                        break
                if not all_available:
                    order_fulfilled = False

        late = 0
        if order_fulfilled and completion_tick is not None:
            if order.deadline_ticks is not None and completion_tick > order.deadline_ticks:
                late = completion_tick - order.deadline_ticks
        elif order.deadline_ticks is not None:
            # If not fulfilled, use max_end_tick for lateness calculation
            if max_end_tick > order.deadline_ticks:
                late = max_end_tick - order.deadline_ticks

        order_outcomes.append(
            OrderOutcome(
                order_id=order.order_id,
                fulfilled=order_fulfilled,
                completion_tick=completion_tick,
                lateness_ticks=late,
            )
        )

    return order_outcomes, max_end_tick, expiry_violations, holding_violations


# ── Objective expression evaluation ──────────────────────────────────────────


def evaluate_objective(
    plan: CompiledPlan,
    blocks: Sequence[ScheduledBlock],
    order_outcomes: Sequence[OrderOutcome] | None = None,
    tick_s: int = _DEFAULT_TICK_S,
) -> float:
    """Evaluate the objective expression for a solution.

    The ``$money_cent_remaining`` expression evaluates to the total
    money_cent_remaining in inventory minus penalties for:
    - Expired entities (weighted by expiry_loss_decay_factor)
    - Late orders
    - Holding rule violations

    Args:
        plan: The compiled planning problem.
        blocks: Scheduled blocks.
        order_outcomes: Pre-computed order outcomes (optional).
        tick_s: Tick duration in seconds.

    Returns:
        The objective value (higher is better).
    """
    if order_outcomes is None:
        order_outcomes, _, _, _ = evaluate_fulfillment(plan, blocks, tick_s)

    # Run inventory simulation to get final state
    snapshots = simulate_inventory(plan, blocks, tick_s)
    final_inventory = snapshots.get(max(snapshots.keys()), {}) if snapshots else {}

    # Count money_cent_remaining in inventory
    money_selector = CompiledSelector(conditions={"type": "money_cent_remaining"}, num=1)
    money_count = _inventory_count(final_inventory, money_selector)

    # Also count any other money-like entities
    money_cent_count = _inventory_count(
        final_inventory, CompiledSelector(conditions={"type": "money_cent"}, num=1)
    )

    total_money = float(money_count + money_cent_count)

    # Penalty: expired entities
    expired_penalty = 0.0
    for b in blocks:
        for consumed in b.consumed:
            expiry_val = consumed.fields.get("expiry")
            if expiry_val is not None:
                expiry_tick = _tick_for_datetime(expiry_val, tick_s)
                if expiry_tick is not None and expiry_tick < b.start_tick:
                    # Expired entity consumed — penalty
                    decay = plan.expiry_loss_decay_factor
                    expired_penalty += consumed.num * 1000 * (1.0 + decay)

    # Penalty: late orders
    late_penalty = 0.0
    for o in order_outcomes:
        if o.fulfilled and o.lateness_ticks > 0:
            late_penalty += o.lateness_ticks * 100  # 100 per tick late

    # Penalty: holding rule violations
    holding_violations, total_excess = _check_holding_rules(plan, final_inventory)
    holding_penalty = float(total_excess) * 500  # 500 per excess unit

    objective = total_money - expired_penalty - late_penalty - holding_penalty

    # Try to evaluate the compiled expression if it's not the default
    if plan.objective_expression != "$money_cent_remaining":
        try:
            fn = compile_expr(
                plan.objective_expression,
                frozenset({"money_cent_remaining", "inventory", "orders"}),
            )
            # Build a simple context for evaluation
            context = {
                "money_cent_remaining": total_money,
                "inventory": {t: len(ents) for t, ents in final_inventory.items()},
                "orders": {o.order_id: o.fulfilled for o in order_outcomes},
            }
            result = fn(**context)
            objective = float(result)
        except Exception as exc:
            logger.warning("Failed to evaluate objective expression: %s", exc)

    return objective


# ── Convenience wrapper ──────────────────────────────────────────────────────


def evaluate_solution(
    plan: CompiledPlan,
    blocks: Sequence[ScheduledBlock],
    tick_s: int = _DEFAULT_TICK_S,
) -> EvaluationResult:
    """Full solution evaluation — returns a structured result.

    This is the single entry point for all constraint checking.
    Use this in benchmarks, tests, and solver comparisons.
    """
    order_outcomes, max_end_tick, expiry_violations, holding_violations = evaluate_fulfillment(
        plan, blocks, tick_s
    )
    objective = evaluate_objective(plan, blocks, order_outcomes, tick_s)

    num_fulfilled = sum(1 for o in order_outcomes if o.fulfilled)
    num_total = len(order_outcomes)

    return EvaluationResult(
        order_outcomes=order_outcomes,
        max_end_tick=max_end_tick,
        expiry_violations=expiry_violations,
        holding_violations=holding_violations,
        objective=objective,
        makespan_s=max_end_tick * tick_s,
        num_blocks=len(blocks),
        num_orders_fulfilled=num_fulfilled,
        num_orders_total=num_total,
        all_orders_fulfilled=num_fulfilled == num_total,
        has_expiry_violations=len(expiry_violations) > 0,
        has_holding_violations=len(holding_violations) > 0,
        correct=(
            num_fulfilled == num_total
            and len(expiry_violations) == 0
            and len(holding_violations) == 0
        ),
    )


# ── Shared logging helper ────────────────────────────────────────────────────


def log_solver_result(
    solver_name: str,
    scheduled_blocks: list,
    order_outcomes: list[OrderOutcome],
    max_end_tick: int,
    solver_time_s: float,
    tick_s: int = _DEFAULT_TICK_S,
) -> None:
    """Log solver result summary in a consistent format.

    All solvers should use this instead of inline logger.info.
    """
    logger.info(
        "%s: %d blocks, %d/%d orders fulfilled, %ds makespan, %.2fs",
        solver_name,
        len(scheduled_blocks),
        sum(1 for o in order_outcomes if o.fulfilled),
        len(order_outcomes),
        max_end_tick * tick_s,
        solver_time_s,
    )