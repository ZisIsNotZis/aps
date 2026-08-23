"""Unified APS schema — strictly typed, zero Any.

The unified model treats everything as flat entities with key/value properties,
transformed by rules (consume/produce), with QBE matching, $ expressions,
and a money-based objective.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# ── Field value types ──────────────────────────────────────────────────────

FieldValue = str | int | float | bool | datetime
"""Valid scalar field values for entity properties and selector conditions."""


def _validate_no_nested(v: object, context: str) -> object:
    """Reject nested dicts/lists in field values before Pydantic type validation."""
    if not isinstance(v, dict):
        return v
    for key, val in v.items():
        if isinstance(val, (dict, list)):
            raise ValueError(f"{context} key {key!r} must be scalar, got {type(val).__name__}")
    return v


# ── Entity ─────────────────────────────────────────────────────────────────


class Entity(BaseModel):
    """Flat key/value entity.

    Reserved fields (expiry, lifetime, datetimeexpr) get auto-precondition
    guards during compilation. All other fields are opaque matching keys.

    When ``count`` > 1, the entity represents ``count`` identical copies.
    The compiler expands these into individual ``CompiledEntity`` objects.
    """

    fields: dict[str, FieldValue]
    count: int = Field(default=1, ge=1)

    @field_validator("fields", mode="before")
    @classmethod
    def _no_nested(cls, v: object) -> object:
        return _validate_no_nested(v, "Entity field")


# ── Selector ───────────────────────────────────────────────────────────────


class Selector(BaseModel):
    """QBE partial object. All specified keys must match; unspecified ignored.

    Values may be concrete scalars or $expressions (strings starting with $).
    """

    conditions: dict[str, FieldValue]
    num: float = Field(default=1.0, gt=0)

    @field_validator("conditions", mode="before")
    @classmethod
    def _no_nested_conditions(cls, v: object) -> object:
        return _validate_no_nested(v, "Selector condition")


# ── Rule ───────────────────────────────────────────────────────────────────


class Rule(BaseModel):
    """Consume/produce transformation with batch semantics.

    Fields:
        consume: Per-unit inputs (x batch qty)
        consume_batch: Per-execution inputs (x 1)
        produce: Per-unit outputs (x batch qty)
        produce_batch: Per-execution outputs (x 1)
        duration_s: Per-unit processing time (x batch qty)
        duration_batch_s: Fixed setup time per execution (x 1)
    """

    rule_id: str = Field(min_length=1, max_length=200)
    batch_min: int = Field(default=1, ge=1)
    batch_max: int = Field(default=100, ge=1)
    consume: dict[str, Selector] = Field(default_factory=dict)
    consume_batch: dict[str, Selector] = Field(default_factory=dict)
    produce: dict[str, Selector] = Field(default_factory=dict)
    produce_batch: dict[str, Selector] = Field(default_factory=dict)
    duration_s: float = Field(default=0.0, ge=0)
    duration_batch_s: float = Field(default=0.0, ge=0)


# ── Order ──────────────────────────────────────────────────────────────────


class Order(BaseModel):
    """Demand with deadline and penalty/bonus rates."""

    order_id: str = Field(min_length=1, max_length=200)
    consume: dict[str, Selector]
    deadline: datetime | None = None
    early_delivery_bonus_per_s: float = Field(default=0.0, ge=0)
    late_delivery_penalty_per_s: float = Field(default=0.0, ge=0)
    release_at: datetime | None = None


# ── HoldingRule ────────────────────────────────────────────────────────────


class HoldingRule(BaseModel):
    """Ongoing cost/constraint on entities in inventory.

    When max is set and inventory exceeds it, the excess triggers
    push-based consumption (the solver must consume to reduce inventory).

    When consume + duration_s are set, the entity consumes other entities
    at the specified rate (e.g., idle equipment costs money per hour).
    """

    selector: Selector
    max: float | None = Field(default=None, ge=0)
    consume: dict[str, Selector] | None = None
    duration_s: float | None = Field(default=None, ge=0)


# ── Objective ──────────────────────────────────────────────────────────────


class Objective(BaseModel):
    """Money-based objective. The solver maximizes the $expression."""

    expression: str = Field(min_length=1)
    expiry_loss_decay_factor: float = Field(default=0.5, ge=0.0, le=1.0)


# ── PlanningModel ──────────────────────────────────────────────────────────


class PlanningModel(BaseModel):
    """Top-level input to the solver."""

    entities: list[Entity]
    rules: list[Rule]
    orders: list[Order]
    holding_rules: list[HoldingRule] = Field(default_factory=list)
    objective: Objective
    planning_start: datetime
    planning_horizon_s: int = Field(ge=1)
    completed_operations: list[dict[str, FieldValue]] = Field(default_factory=list)
    locked_operations: list[dict[str, FieldValue]] = Field(default_factory=list)
    freeze_fence_s: int = Field(default=0, ge=0)
