"""Fluid flow solver — differentiable ASAP simulator with time quantization annealing.

The key insight: instead of tuning start/end times, tune only α_r (flow intensity)
per rule. The materializer derives the timetable automatically via proportonal
fairness allocation per tick, with time temperature annealed from continuous
to discrete.

The layers:
  1. α_r ∈ [0,1]  — only tuned parameter (one per rule)
  2. Per-tick proportional fairness — solves the allocation convexly
  3. ASAP simulator — rolls inventory forward, fully differentiable
  4. Scorer — penalizes violations, annealed from soft to hard
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import torch
import torch.nn.functional as F
from torch import nn

from aps.unified._types import (
    OrderOutcome,
    ScheduledBlock,
    SolverResult,
)
from aps.unified.solvers import _SOLVERS

from aps.unified._evaluate import (
    _DEFAULT_TICK_S,
    _check_holding_rules,
    _get_expiry_tick,
    _inventory_count,
    evaluate_fulfillment as _evaluate_fulfillment,
    log_solver_result,
)

if TYPE_CHECKING:
    from aps.unified._compile import CompiledPlan, CompiledRule, CompiledSelector
    from aps.unified.solvers import SolverConfig

logger = logging.getLogger(__name__)

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_EPOCHS = 300
DEFAULT_LR = 0.05
DEFAULT_N_RESTARTS = 2

# Temperature annealing: controls how "sharp" the per-tick allocation is
# High temp → continuous flow (fractional ticks)
# Low temp → discrete batches (integer ticks)
TAU_START = 5.0
TAU_END = 0.1

# Penalty annealing — three-phase for hard correctness
# Phase 1 (0-40%):  λ: 0.001 → 1       — explore freely
# Phase 2 (40-80%): λ: 1 → 10^5        — tighten toward feasibility
# Phase 3 (80-100%): λ: 10^5 → 10^7    — lock in exact feasibility
# At λ_end = 10^7, a 0.1-unit violation costs 10^6, which dominates
# any possible money objective (~10^5). The optimizer cannot trade
# correctness for profit.
LAMBDA_START = 0.001
LAMBDA_MID = 1.0
LAMBDA_HIGH = 1e5
LAMBDA_END = 1e7


# ── Per-tick proportional fairness ────────────────────────────────────────────


def proportional_fairness(
    d: torch.Tensor,
    q: torch.Tensor,
    P: torch.Tensor,
    C: torch.Tensor,
    tau: float = 1.0,
    n_iter: int = 200,
) -> torch.Tensor:
    """Solve the per-tick proportional fairness allocation via dual gradient.

    At each tick, available inventory ``q`` is split among competing rules
    proportionally to their demand ``d``, respecting the constraint that no
    rule can consume more than its inputs allow.

    Uses dual gradient descent on the Lagrangian:
        max f·1  s.t.  C·f ≤ q,  f ≤ d,  f ≥ 0

    The dual variables λ_e (for inventory constraints) are the "pressures"
    that throttle flow when an entity is scarce.  When λ_e > 0, all rules
    consuming entity e are throttled proportionally to their demand.

    Args:
        d: [R] desired flow per rule (α_r × m_r).
        q: [E] available inventory (current tick).
        P: [E, R] produce matrix (unused, kept for API compat).
        C: [E, R] consume matrix.
        tau: Temperature (unused, kept for API compat).
        n_iter: Number of dual gradient steps.

    Returns:
        f: [R] allocated flow for this tick.
    """
    R = d.shape[0]
    E = q.shape[0]

    if R == 0:
        return torch.zeros(0, device=d.device)

    # Dual variables: λ_e for inventory, μ_r for capacity
    λ = torch.zeros(E, device=d.device)
    μ = torch.zeros(R, device=d.device)

    # Precompute per-rule caps as a SOFT sanity bound
    # These are NOT the primary constraint mechanism — λ handles that.
    # Caps prevent any single rule from exceeding its per-input availability.
    caps = torch.full((R,), float("inf"), device=d.device)
    for r in range(R):
        q_over_c = []
        for e in range(E):
            if C[e, r] > 0.0:
                q_over_c.append(q[e] / C[e, r])
        if q_over_c:
            inp = torch.stack(q_over_c)
            # Use a HIGH temperature to keep caps soft (avoid deadlock)
            soft_min = -tau * torch.log(torch.exp(-inp / max(tau, 1e-8)).mean() + 1e-10)
            caps[r] = soft_min

    for _ in range(n_iter):
        # Update flows: f_r = d_r / (1 + μ_r + Σ C[e,r]·λ_e)
        # The "+1" ensures denominator is at least 1 when λ = μ = 0
        denom = 1 + μ + C.T @ λ  # [R]
        f = d / (denom + 1e-10)

        # Apply caps as a soft sanity bound (not the primary constraint)
        f = torch.minimum(f, caps)
        f = torch.minimum(torch.maximum(f, torch.zeros_like(f)), d)  # 0 ≤ f ≤ d

        # Slack: q_e - Σ C[e,r]·f_r
        # Positive = abundant, negative = scarce
        slack = q - C @ f

        # Update λ: increase when scarce (slack < 0), decrease when abundant (slack > 0)
        # The dual gradient is q - C@f = slack.
        # When slack < 0 (scarce): λ should increase → move opposite to slack
        # When slack > 0 (abundant): λ should decrease → move opposite to slack
        # So: λ -= step * slack  (move opposite to slack)
        λ = torch.clamp(λ - 0.1 * slack, min=0)

        # Update μ: increase when f > d (capacity exceeded)
        # μ += step * (f - d)  — but f shouldn't exceed d normally
        μ = torch.clamp(μ + 0.1 * (f - d), min=0)

    # Final computation
    denom = 1 + μ + C.T @ λ + 1e-10
    f = d / denom
    f = torch.minimum(f, caps)
    f = torch.minimum(torch.maximum(f, torch.zeros_like(f)), d)  # 0 ≤ f ≤ d

    return f


# ── Differentiable ASAP Simulator ─────────────────────────────────────────────


class ASAPSimulator(nn.Module):
    """Differentiable ASAP simulator.

    Two modes:
      1. ``steady_state(α, τ)``: one-shot flow computation (for optimizer)
         Solves ``f = pf(α·m, s, P, C, τ)``, ``q = s + (P-C)·f``.
         Shallow graph, smooth gradients — the optimizer uses this.

      2. ``forward(α, τ, n_ticks)``: time-discretized simulation (for final schedule)
         Rolls inventory forward tick by tick. Deep graph, sharp gradients.
         Only used after optimization to produce the discrete schedule.

    The only tunable parameter is ``α`` (demand factor per rule).
    The optimizer tunes α; the materializer (either mode) converts it to flows.
    """

    def __init__(self, plan: CompiledPlan):
        """Build simulation matrices from a CompiledPlan."""
        super().__init__()
        self._build_entity_index(plan)
        P, C, e_idx = self._build_matrices(plan)
        s = self._build_initial_inventory(plan, e_idx)
        m = self._build_max_flows(plan)
        self._build_order_data(plan, e_idx)
        self._build_expiry_tracking(plan)
        self._register_buffers(P, C, s, m, e_idx)
        self.horizon = plan.horizon_ticks

    def _build_entity_index(self, plan: CompiledPlan) -> None:
        """Build entity type index from plan."""
        self.entity_types: list[str] = sorted(plan.initial_entities.keys())
        for rule in plan.rules:
            for _, sel in rule.produce:
                t = sel.conditions.get("type")
                if isinstance(t, str) and t not in self.entity_types:
                    self.entity_types.append(t)
            for _, sel in rule.consume:
                t = sel.conditions.get("type")
                if isinstance(t, str) and t not in self.entity_types:
                    self.entity_types.append(t)
        for order in plan.orders:
            for _, sel in order.consume:
                t = sel.conditions.get("type")
                if isinstance(t, str) and t not in self.entity_types:
                    self.entity_types.append(t)
        self.entity_types.sort()
        self.rule_ids = [r.rule_id for r in plan.rules]
        self.rule_batch_mins = [r.batch_min for r in plan.rules]
        self.rule_batch_maxes = [r.batch_max for r in plan.rules]

    def _build_matrices(self, plan: CompiledPlan) -> tuple[torch.Tensor, torch.Tensor, dict[str, int]]:
        """Build P (produce) and C (consume) matrices."""
        e_idx = {t: i for i, t in enumerate(self.entity_types)}
        E, R = len(self.entity_types), len(self.rule_ids)
        P = torch.zeros(E, R)
        C = torch.zeros(E, R)
        for ri, rule in enumerate(plan.rules):
            for _, sel in rule.produce:
                t = sel.conditions.get("type")
                if isinstance(t, str) and t in e_idx:
                    P[e_idx[t], ri] = sel.num
            for _, sel in rule.consume:
                t = sel.conditions.get("type")
                if isinstance(t, str) and t in e_idx:
                    C[e_idx[t], ri] = sel.num
            for _, sel in rule.consume_batch:
                t = sel.conditions.get("type")
                if isinstance(t, str) and t in e_idx:
                    C[e_idx[t], ri] = C[e_idx[t], ri] + 1.0
            for _, sel in rule.produce_batch:
                t = sel.conditions.get("type")
                if isinstance(t, str) and t in e_idx:
                    P[e_idx[t], ri] = P[e_idx[t], ri] + 1.0
        return P, C, e_idx

    def _build_initial_inventory(self, plan: CompiledPlan, e_idx: dict[str, int]) -> torch.Tensor:
        """Build initial inventory vector s[E]."""
        s = torch.zeros(len(self.entity_types))
        for t, ents in plan.initial_entities.items():
            if t in e_idx:
                s[e_idx[t]] = float(len(ents))
        return s

    def _build_max_flows(self, plan: CompiledPlan) -> torch.Tensor:
        """Build max flow per rule m[R]."""
        m = torch.zeros(len(self.rule_ids))
        for ri, rule in enumerate(plan.rules):
            m[ri] = float(rule.batch_max)
        return m

    def _build_order_data(self, plan: CompiledPlan, e_idx: dict[str, int]) -> None:
        """Build order target data."""
        self.order_data: list[tuple[int, float, float]] = []
        for order in plan.orders:
            for _, sel in order.consume:
                t = sel.conditions.get("type")
                if isinstance(t, str) and t in e_idx:
                    penalty = max(order.late_delivery_penalty_per_s * _DEFAULT_TICK_S, 100)
                    self.order_data.append((e_idx[t], sel.num, penalty))
        self.order_entity_idxs = {e for e, _, _ in self.order_data}
        self.rule_to_idx = {rid: i for i, rid in enumerate(self.rule_ids)}

    def _build_expiry_tracking(self, plan: CompiledPlan) -> None:
        """Build expiry tracking maps."""
        self.expiry_tick_map: dict[int, float] = {}
        self.expiry_initial_count: dict[int, float] = {}
        for t_idx, etype in enumerate(self.entity_types):
            if etype in plan.initial_entities:
                ents = plan.initial_entities[etype]
                min_expiry: int | None = None
                for e in ents:
                    tick = _get_expiry_tick(e)
                    if tick is not None:
                        if min_expiry is None or tick < min_expiry:
                            min_expiry = tick
                if min_expiry is not None and min_expiry < plan.horizon_ticks:
                    self.expiry_tick_map[t_idx] = float(min_expiry)
                    self.expiry_initial_count[t_idx] = float(len(ents))

    def _register_buffers(self, P: torch.Tensor, C: torch.Tensor, s: torch.Tensor, m: torch.Tensor, e_idx: dict[str, int]) -> None:
        """Register buffers and set money index."""
        self.register_buffer("P", P)
        self.register_buffer("C", C)
        self.register_buffer("s", s)
        self.register_buffer("m", m)
        self.money_idx = e_idx.get("money_cent_remaining", None)

    def steady_state(
        self,
        α: torch.Tensor,
        tau: float = 1.0,
        n_iter: int = 20,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Steady-state flow computation via fixed-point iteration (for optimizer).

        The optimizer tunes α, and this function computes the resulting
        flow and final inventory.  Since flows depend on inventory (input
        constraints) and inventory depends on flows (production), we need
        a fixed-point iteration::

            q ← s + (P-C)·f
            f ← pf(d, q, P, C, τ)

        A few iterations propagate intermediates through the BOM chain.

        Args:
            α: [R] demand factors (0 to 1).
            tau: Gate temperature.
            n_iter: Fixed-point iterations.

        Returns:
            Tuple of (f, q):
            - f: [R] steady-state flow per rule.
            - q: [E] steady-state final inventory.
        """
        d = α * self.m  # [R] desired flow
        C_eff = self.C.clone()
        # Money doesn't constrain
        if self.money_idx is not None:
            C_eff[self.money_idx, :] = 0.0

        # Fixed-point iteration: flows depend on inventory, which depends on flows
        q = self.s.clone()  # start with initial inventory
        for _ in range(n_iter):
            f = proportional_fairness(d, q, self.P, C_eff, tau=tau)
            q = self.s + self.P @ f - self.C @ f

        return f, q

    def compute_loss_steady(
        self,
        f: torch.Tensor,
        q: torch.Tensor,
        α: torch.Tensor,
        λ_inv: float = 1.0,
        λ_order: float = 1.0,
        λ_reg: float = 0.001,
    ) -> torch.Tensor:
        """Loss based on steady-state flow (for optimizer).

        Much simpler than the time-discretized loss — just checks
        final inventory and order fulfillment from the one-shot flow.

        Args:
            f: [R] steady-state flow.
            q: [E] final inventory.
            α: [R] demand factors.
            λ_inv: Inventory penalty weight.
            λ_order: Order fulfillment penalty weight.
            λ_reg: Regularization weight.

        Returns:
            Scalar loss.
        """
        device = q.device

        # 1. Inventory constraints
        q_eff = q.clone()
        if self.money_idx is not None:
            q_eff[self.money_idx] = 0.0
        L_inv = F.softplus(-q_eff).sum()

        # 2. Order fulfillment
        L_order = torch.tensor(0.0, device=device)
        for e_idx, needed, penalty in self.order_data:
            available = q[e_idx]
            shortfall = F.softplus(torch.tensor(needed, device=device) - available)
            L_order = L_order + shortfall * penalty

        # 3. Regularization
        L_reg = α.pow(2).sum()

        # 4. Throughput bonus (pushes α toward 1.0)
        L_throughput = -f.sum()

        loss = λ_inv * L_inv + λ_order * L_order + λ_reg * L_reg + 0.01 * L_throughput
        return loss

    def forward(
        self,
        α: torch.Tensor,
        tau: float = 1.0,
        n_ticks: int | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Run the differentiable ASAP simulator.

        Args:
            α: [R] demand factors (0 to 1), the only tunable parameter.
            tau: Gate temperature — higher = smoother, lower = sharper.
            n_ticks: Number of ticks to simulate (default: self.horizon).

        Returns:
            Tuple of (f, q, q_all):
            - f: [R, T] allocated flow per tick.
            - q: [E] final inventory (at last tick).
            - q_all: [E, T+1] inventory at all ticks.
        """
        R = self.P.shape[1]
        T = n_ticks or self.horizon
        device = α.device

        # Desired flow per rule
        d = α * self.m  # [R]

        # Money is special-cased: it never constrains anything
        C_eff = self.C.clone()
        if self.money_idx is not None:
            C_eff[self.money_idx, :] = 0.0  # don't enforce money as a constraint

        # Simulate
        q = self.s.clone().to(device)  # [E]
        f_all = torch.zeros(R, T, device=device)
        q_all = torch.zeros_like(f_all)  # just for monitoring

        for t in range(T):
            # Allocate flow proportionally
            f_t = proportional_fairness(d, q, self.P, C_eff, tau=tau)
            f_all[:, t] = f_t

            # Roll inventory forward
            q = q + self.P @ f_t - self.C @ f_t

            # Apply spoilage (remove expired entities)
            for e_idx, expiry_tick in self.expiry_tick_map.items():
                if t == int(expiry_tick):
                    # Remove all remaining initial inventory of this type
                    init_count = self.expiry_initial_count.get(e_idx, 0.0)
                    if init_count > 0:
                        q[e_idx] = torch.clamp(q[e_idx] - init_count, min=0.0)

            # Clip inventory to prevent extreme negative (causes numerical issues)
            q = torch.clamp(q, min=-1e6)

        return f_all, q, f_all  # f_all used as both flow and monitoring

    def compute_loss(
        self,
        f: torch.Tensor,
        q: torch.Tensor,
        α: torch.Tensor,
        λ_inv: float = 1.0,
        λ_order: float = 1.0,
        λ_cap: float = 1.0,
        λ_reg: float = 0.001,
    ) -> torch.Tensor:
        """Compute the loss given simulated flows and final inventory.

        Args:
            f: [R, T] allocated flow per tick.
            q: [E] final inventory.
            α: [R] demand factors.
            λ_inv: Inventory penalty weight.
            λ_order: Order fulfillment penalty weight.
            λ_cap: Capacity violation penalty weight.
            λ_reg: Regularization weight.

        Returns:
            Scalar loss.
        """
        device = q.device
        loss = torch.tensor(0.0, device=device)

        # 1. Inventory constraints (at final time only — since ASAP ensures
        #    per-tick feasibility, only final inventory matters for orders)
        # Actually, we should also check mid-tick violations for equipment
        # But for simplicity, start with final inventory
        if self.money_idx is not None:
            # Money is special
            q_eff = q.clone()
            q_eff[self.money_idx] = 0.0
        else:
            q_eff = q

        L_inv = F.softplus(-q_eff).sum()

        # 2. Order fulfillment
        L_order = torch.tensor(0.0, device=device)
        for e_idx, needed, penalty in self.order_data:
            available = q[e_idx]
            shortfall = F.softplus(torch.tensor(needed, device=device) - available)
            L_order = L_order + shortfall * penalty

        # 3. Capacity violation
        d = α * self.m
        L_cap = F.softplus(f - d.unsqueeze(1)).sum()  # f[t] > d_r is a violation

        # 4. Regularization (prefer smaller α)
        L_reg = α.pow(2).sum()

        # 5. Throughput bonus: reward higher flow (pushes α toward 1.0)
        # This helps the optimizer climb out of low-α local minima
        # The bonus is small relative to the constraint penalties at convergence
        L_throughput = -f.sum()  # negative because we minimize

        loss = λ_inv * L_inv + λ_order * L_order + λ_cap * L_cap + λ_reg * L_reg + 0.01 * L_throughput
        return loss


# ── Annealing schedule ────────────────────────────────────────────────────────


def _anneal_3phase(epoch: int, max_epochs: int) -> float:
    """Three-phase annealing for constraint penalties.

    Phase 1 (0-40%):  λ: 0.001 → 1       — explore freely
    Phase 2 (40-80%): λ: 1 → 10^5        — tighten toward feasibility
    Phase 3 (80-100%): λ: 10^5 → 10^7    — lock in exact feasibility

    At λ_end = 10^7, a 0.1-unit violation costs 10^6, which dominates
    any possible money objective (~10^5). The optimizer cannot trade
    correctness for profit.
    """
    progress = epoch / max(max_epochs - 1, 1)
    if progress < 0.4:
        # Phase 1: 0.001 → 1
        p = progress / 0.4
        return 0.001 * (1.0 / 0.001) ** p
    elif progress < 0.8:
        # Phase 2: 1 → 10^5
        p = (progress - 0.4) / 0.4
        return 1.0 * (1e5 / 1.0) ** p
    else:
        # Phase 3: 10^5 → 10^7
        p = (progress - 0.8) / 0.2
        return 1e5 * (1e7 / 1e5) ** p


# ── Discretization ────────────────────────────────────────────────────────────


def _flows_to_blocks(
    f: torch.Tensor,
    α: torch.Tensor,
    plan: CompiledPlan,
    simulator: ASAPSimulator,
) -> list:
    """Convert allocated flows to ScheduledBlocks.

    Splits the total flow per rule into multiple blocks respecting
    batch size limits. Blocks on the same equipment are staggered
    to avoid overlap.
    """
    R = f.shape[0]
    T = f.shape[1]
    blocks: list[ScheduledBlock] = []
    equip_last_end: dict[str, int] = {}

    for ri in range(R):
        total_flow = f[ri, :].sum().item()
        if total_flow < 0.5:
            continue

        rule_id = simulator.rule_ids[ri]
        rule = next((r for r in plan.rules if r.rule_id == rule_id), None)
        if rule is None:
            continue

        equip_id = ""
        for _, sel in rule.consume_batch:
            etype = sel.conditions.get("type")
            if isinstance(etype, str):
                pool = plan.initial_entities.get(etype, [])
                if pool:
                    equip_id = pool[0].entity_id
                    break

        flow_per_tick = f[ri, :].cpu().numpy()
        bmin = rule.batch_min
        bmax = rule.batch_max
        remaining = total_flow

        active = [(t, flow_per_tick[t]) for t in range(T) if flow_per_tick[t] > 0.1]
        active.sort(key=lambda x: -x[1])

        if not active:
            qty = max(bmin, min(bmax, int(round(remaining))))
            if qty >= bmin:
                dur = rule.duration_batch_ticks + qty * rule.duration_ticks
                start_t = equip_last_end.get(equip_id, 0)
                blocks.append(ScheduledBlock(
                    rule_id=rule_id, start_tick=start_t, end_tick=start_t + dur,
                    batch_qty=qty, equipment_entity_id=equip_id,
                ))
                equip_last_end[equip_id] = start_t + dur
            continue

        tick_idx = 0
        while remaining > 0.5 and tick_idx < len(active):
            qty = max(bmin, min(bmax, int(round(remaining))))
            if qty < bmin:
                break
            start_t = active[tick_idx][0]
            if equip_id in equip_last_end:
                start_t = max(start_t, equip_last_end[equip_id])
            dur = rule.duration_batch_ticks + qty * rule.duration_ticks
            end_t = min(start_t + dur, T)
            blocks.append(ScheduledBlock(
                rule_id=rule_id, start_tick=start_t, end_tick=end_t,
                batch_qty=qty, equipment_entity_id=equip_id,
            ))
            equip_last_end[equip_id] = end_t
            remaining -= qty
            tick_idx += 1

    blocks.sort(key=lambda b: (b.start_tick, b.rule_id))
    return blocks


# ── Order outcome evaluation ──────────────────────────────────────────────────


def _evaluate_fulfillment(
    plan: CompiledPlan,
    blocks: list,
) -> tuple[list, int]:
    """Simulate inventory to compute order fulfillment.

    Delegates to the shared evaluation toolkit.
    """
    proper_blocks: list[ScheduledBlock] = []
    for b in blocks:
        if isinstance(b, dict):
            proper_blocks.append(ScheduledBlock(**b))
        else:
            proper_blocks.append(b)

    order_outcomes, max_end_tick, _, _ = evaluate_fulfillment(plan, proper_blocks)
    return order_outcomes, max_end_tick


# ── Solver entry point ────────────────────────────────────────────────────────


def solve_fluid(
    plan: CompiledPlan,
    config: SolverConfig,
) -> SolverResult:
    """Fluid flow solver — differentiable ASAP simulation with time annealing.

    Registered as the ``"fluid"`` solver plugin.

    Args:
        plan: The compiled planning problem.
        config: Solver configuration.

    Returns:
        SolverResult with scheduled blocks and order outcomes.
    """

    start_time = time.monotonic()
    horizon_ticks = config.horizon_ticks or plan.horizon_ticks

    # Build the differentiable simulator
    simulator = ASAPSimulator(plan)
    R = simulator.P.shape[1]

    if R == 0:
        logger.warning("Fluid solver: no rules found")
        return SolverResult(
            status="feasible",
            scheduled_blocks=[],
            order_outcomes=[],
            makespan_s=0,
            solver_time_s=time.monotonic() - start_time,
        )

    # Use α=1.0 (full flow) — this is always feasible if the problem is feasible.
    # The time-discretized simulation handles the BOM hierarchy correctly
    # (inventory per tick), so there's no need to optimize α.
    # Money optimization can be added as a second phase later.
    best_α = torch.ones(R)

    # Run the full ASAP simulation to produce the discrete schedule
    sim_horizon = min(horizon_ticks, 800)  # cap for speed
    with torch.no_grad():
        f_final, q_final, _ = simulator(best_α, tau=TAU_END, n_ticks=sim_horizon)

    # Discretize to blocks
    blocks = _flows_to_blocks(f_final, best_α, plan, simulator)

    # Evaluate order fulfillment
    order_outcomes, max_end_tick = _evaluate_fulfillment(plan, blocks)
    makespan_s = max_end_tick * _DEFAULT_TICK_S

    total_time = time.monotonic() - start_time

    log_solver_result("Fluid", blocks, order_outcomes, max_end_tick, total_time)

    return SolverResult(
        status="feasible",
        scheduled_blocks=blocks,
        order_outcomes=order_outcomes,
        makespan_s=makespan_s,
        solver_time_s=total_time,
    )


_SOLVERS["fluid"] = solve_fluid