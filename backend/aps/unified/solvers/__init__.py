"""Solver plugin system — register and dispatch solver implementations.

Solvers live in this directory and register via the ``@register_solver``
decorator.  The dispatch entry point ``run_solver(plan, config)`` looks up
the named solver and calls it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:

    from aps.unified._compile import CompiledPlan
    from aps.unified._types import SolverResult


@dataclass
class SolverConfig:
    """Configuration passed to every solver plugin.

    Attributes:
        solver: Name of the solver to run ("greedy" | "cp_sat").
        time_limit_s: Wall-clock time limit for the solver.
        objective_expression: The ``$expression`` to optimize.
            ``None`` means the caller wants the solver's default objective.
        horizon_ticks: Planning horizon in ticks (from CompiledPlan).
    """

    solver: str = "cp_sat"
    time_limit_s: float = 60.0
    objective_expression: str | None = None
    horizon_ticks: int = 0


# ── Plugin registry ────────────────────────────────────────────────────────

_SOLVERS: dict[str, Callable[..., object]] = {}  # populated by solver plugins at import time


def register_solver(name: str) -> Callable[[Callable[..., object]], Callable[..., object]]:
    """Decorator that registers a solver function under *name*.

    Usage::

        @register_solver("greedy")
        def greedy_solve(plan: CompiledPlan, config: SolverConfig) -> SolverResult:
            ...
    """

    def decorator(fn: Callable[..., object]) -> Callable[..., object]:
        _SOLVERS[name] = fn
        return fn

    return decorator


def run_solver(
    plan: CompiledPlan,
    config: SolverConfig,
) -> SolverResult:
    """Dispatch to the solver named in *config* and return its result."""
    from aps.unified._types import SolverResult

    fn = _SOLVERS.get(config.solver)
    if fn is None:
        available = ", ".join(sorted(_SOLVERS))
        msg = f"Unknown solver {config.solver!r}. Available: {available}"
        raise ValueError(msg)
    result = fn(plan, config)
    assert isinstance(result, SolverResult), (
        f"Solver {config.solver!r} returned {type(result).__name__}, expected SolverResult"
    )
    return result  # type: ignore[return-value]
