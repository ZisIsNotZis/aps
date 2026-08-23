"""Shared result types for all solvers.

Separated from _solve.py to break the circular dependency:
  _solve.py → solvers/*.py → _solve.py

Types defined here have no solver dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class EntitySnapshot:
    """Snapshot of an entity consumed or produced by a scheduled block."""

    entity_type: str  # entity type signature
    num: float
    fields: dict[str, object]  # key fields for identification


@dataclass(frozen=True)
class ScheduledBlock:
    """A scheduled rule execution."""

    rule_id: str
    start_tick: int
    end_tick: int
    batch_qty: int
    equipment_entity_id: str  # the equipment entity used
    consumed: list[EntitySnapshot] = field(default_factory=list)
    produced: list[EntitySnapshot] = field(default_factory=list)


@dataclass(frozen=True)
class OrderOutcome:
    """Result for a single order."""

    order_id: str
    fulfilled: bool
    completion_tick: int | None
    lateness_ticks: int


@dataclass(frozen=True)
class SolverResult:
    """Result of a solver run."""

    status: Literal["optimal", "feasible", "timeout"]
    scheduled_blocks: list[ScheduledBlock] = field(default_factory=list)
    order_outcomes: list[OrderOutcome] = field(default_factory=list)
    makespan_s: int = 0
    solver_time_s: float = 0.0
    solution_curve: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class EvaluationResult:
    """Full solution evaluation — structured result from evaluate_solution()."""

    order_outcomes: list[OrderOutcome]
    max_end_tick: int
    expiry_violations: list[str]
    holding_violations: list[str]
    objective: float
    makespan_s: int
    num_blocks: int
    num_orders_fulfilled: int
    num_orders_total: int
    all_orders_fulfilled: bool
    has_expiry_violations: bool
    has_holding_violations: bool
    correct: bool

    @classmethod
    def from_dict(cls, d: dict) -> EvaluationResult:
        return cls(**d)