"""Compiler — validate → normalize → compile PlanningModel to CompiledPlan.

Produces a frozen, immutable intermediate representation that the solver
consumes. All validation happens here; the solver trusts its input.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from aps.unified._schema import FieldValue, PlanningModel, Selector

# ── Tick resolution ────────────────────────────────────────────────────────

_DEFAULT_TICK_S = 60  # 1-minute ticks


# ── Compiled IR types ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class CompiledEntity:
    """Immutable snapshot of an entity at compile time."""

    entity_id: str
    fields: Mapping[str, FieldValue]
    signature: str  # deterministic hash of fields for grouping


@dataclass(frozen=True)
class CompiledSelector:
    """Resolved selector with concrete conditions."""

    conditions: Mapping[str, FieldValue]
    num: float


@dataclass(frozen=True)
class CompiledRule:
    """Compiled rule ready for the solver."""

    rule_id: str
    batch_min: int
    batch_max: int
    consume: Sequence[tuple[str, CompiledSelector]]
    consume_batch: Sequence[tuple[str, CompiledSelector]]
    produce: Sequence[tuple[str, CompiledSelector]]
    produce_batch: Sequence[tuple[str, CompiledSelector]]
    duration_ticks: int
    duration_batch_ticks: int


@dataclass(frozen=True)
class CompiledOrder:
    """Compiled order with tick-based deadline."""

    order_id: str
    consume: Sequence[tuple[str, CompiledSelector]]
    deadline_ticks: int | None
    early_delivery_bonus_per_s: float
    late_delivery_penalty_per_s: float
    release_tick: int | None


@dataclass(frozen=True)
class CompiledHoldingRule:
    """Compiled holding rule."""

    selector: CompiledSelector
    max: float | None
    consume: Sequence[tuple[str, CompiledSelector]] | None
    duration_s: float | None


@dataclass(frozen=True)
class CompiledPlan:
    """Immutable planning IR. The solver reads this; it never mutates it."""

    rules: Sequence[CompiledRule] = field(default_factory=list)
    orders: Sequence[CompiledOrder] = field(default_factory=list)
    initial_entities: Mapping[str, Sequence[CompiledEntity]] = field(default_factory=dict)
    holding_rules: Sequence[CompiledHoldingRule] = field(default_factory=list)
    horizon_ticks: int = 0
    objective_expression: str = "$money_cent_remaining"
    expiry_loss_decay_factor: float = 0.5


# ── CompileError ───────────────────────────────────────────────────────────


class CompileError(Exception):
    """Raised when the model fails validation during compilation."""


# ── Helpers ────────────────────────────────────────────────────────────────


def _entity_signature(fields: Mapping[str, FieldValue]) -> str:
    """Deterministic hash of entity fields for grouping."""
    # Sort keys for deterministic output
    serialized = json.dumps(
        {k: _serialize_field(v) for k, v in sorted(fields.items())},
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


def _serialize_field(v: FieldValue) -> str | int | float | bool:
    """Serialize a field value to a JSON-compatible type."""
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def _to_ticks(seconds: float, tick_s: int = _DEFAULT_TICK_S) -> int:
    """Convert seconds to integer ticks, rounding up."""
    return max(1, int(seconds / tick_s + 0.5))


def _datetime_to_tick(dt: datetime, start: datetime, tick_s: int = _DEFAULT_TICK_S) -> int:
    """Convert absolute datetime to tick offset from planning start."""
    delta_s = (dt - start).total_seconds()
    return max(0, int(delta_s / tick_s + 0.5))


def _compile_selector(s: Selector) -> CompiledSelector:
    """Compile a single selector."""
    return CompiledSelector(
        conditions={k: v for k, v in s.conditions.items()},
        num=s.num,
    )


def _compile_selectors(
    selectors: dict[str, Selector],
) -> list[tuple[str, CompiledSelector]]:
    """Compile a dict of named selectors to a sorted list."""
    return [(name, _compile_selector(s)) for name, s in sorted(selectors.items())]


# ── Main compile function ──────────────────────────────────────────────────


def compile_model(model: PlanningModel, tick_s: int = _DEFAULT_TICK_S) -> CompiledPlan:
    """Validate, normalize, and compile a PlanningModel into a CompiledPlan.

    Args:
        model: The planning model to compile.
        tick_s: Tick duration in seconds (default 60).

    Returns:
        A frozen CompiledPlan ready for the solver.

    Raises:
        CompileError: if validation fails (duplicate IDs, etc.).
    """
    # ── Validate ───────────────────────────────────────────────────────
    rule_ids: set[str] = set()
    for r in model.rules:
        if r.rule_id in rule_ids:
            raise CompileError(f"duplicate rule_id: {r.rule_id!r}")
        rule_ids.add(r.rule_id)

    order_ids: set[str] = set()
    for o in model.orders:
        if o.order_id in order_ids:
            raise CompileError(f"duplicate order_id: {o.order_id!r}")
        order_ids.add(o.order_id)

    # ── Normalize entities ─────────────────────────────────────────────
    # Expand `count` into individual compiled entities, then group by signature.
    entities_by_type: dict[str, list[CompiledEntity]] = {}
    eid_counter = 0
    for entity in model.entities:
        fields = entity.fields
        entity_type = fields.get("type")
        type_key = entity_type if isinstance(entity_type, str) else _entity_signature(fields)

        for _ in range(entity.count):
            compiled = CompiledEntity(
                entity_id=f"e{eid_counter:04d}",
                fields=fields,
                signature=type_key,
            )
            entities_by_type.setdefault(type_key, []).append(compiled)
            eid_counter += 1

    # ── Compile rules ──────────────────────────────────────────────────
    compiled_rules: list[CompiledRule] = []
    for r in model.rules:
        compiled_rules.append(
            CompiledRule(
                rule_id=r.rule_id,
                batch_min=r.batch_min,
                batch_max=r.batch_max,
                consume=_compile_selectors(r.consume),
                consume_batch=_compile_selectors(r.consume_batch),
                produce=_compile_selectors(r.produce),
                produce_batch=_compile_selectors(r.produce_batch),
                duration_ticks=_to_ticks(r.duration_s, tick_s),
                duration_batch_ticks=_to_ticks(r.duration_batch_s, tick_s),
            )
        )

    # ── Compile orders ─────────────────────────────────────────────────
    compiled_orders: list[CompiledOrder] = []
    for o in model.orders:
        deadline_ticks = None
        if o.deadline is not None:
            deadline_ticks = _datetime_to_tick(o.deadline, model.planning_start, tick_s)

        release_tick = None
        if o.release_at is not None:
            release_tick = _datetime_to_tick(o.release_at, model.planning_start, tick_s)

        compiled_orders.append(
            CompiledOrder(
                order_id=o.order_id,
                consume=_compile_selectors(o.consume),
                deadline_ticks=deadline_ticks,
                early_delivery_bonus_per_s=o.early_delivery_bonus_per_s,
                late_delivery_penalty_per_s=o.late_delivery_penalty_per_s,
                release_tick=release_tick,
            )
        )

    # ── Compile holding rules ──────────────────────────────────────────
    compiled_holding: list[CompiledHoldingRule] = []
    for hr in model.holding_rules:
        compiled_holding.append(
            CompiledHoldingRule(
                selector=_compile_selector(hr.selector),
                max=hr.max,
                consume=_compile_selectors(hr.consume) if hr.consume else None,
                duration_s=hr.duration_s,
            )
        )

    # ── Horizon ────────────────────────────────────────────────────────
    horizon_ticks = _to_ticks(model.planning_horizon_s, tick_s)

    return CompiledPlan(
        rules=compiled_rules,
        orders=compiled_orders,
        initial_entities=entities_by_type,
        holding_rules=compiled_holding,
        horizon_ticks=horizon_ticks,
        objective_expression=model.objective.expression,
        expiry_loss_decay_factor=model.objective.expiry_loss_decay_factor,
    )
