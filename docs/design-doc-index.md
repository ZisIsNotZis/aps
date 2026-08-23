# APS Design Docs Index

## Canonical doc (single source of truth)

1. `docs/unified-aps-model.md`
   **Single source of truth** for kernel semantics: unified entity model, rule shape,
   QBE matching, $ expressions, auto-preconditions, orders, money-based objective,
   holding rules, and replanning semantics. Supersedes all previous docs.

## Reference-only docs (kept for context)

All archived docs are in `docs/archive/`:

- `archive/discrete-factory-rule-catalog.md` — Industrial YAML examples and hard cases
- `archive/item-function-aps-decision-register.md` — Decision register, rejected paths, open decisions
- `archive/item-function-aps-architecture.md` — Module-level architecture for the item_function subsystem
- `archive/item-function-aps-tdd-implementation-plan.md` — Original TDD implementation plan
- `archive/resource-centric-aps-model-plan.md` — Research anchors and cross-industry scenarios
- `archive/universal-aps-architecture.md` — Design alternatives and configuration workbench
- `archive/universal-aps-implementation-plan.md` — 10-phase implementation plan
- `archive/universal-aps-implementation-roadmap.md` — High-level roadmap
- `archive/universal-aps-rich-runtime-plan.md` — Frontend audit and rich field kinds
- `archive/proposal.md` — Original $expression and holding rule proposal
- `archive/phases.md` — Legacy planner improvement phases

These documents reflect earlier phases and intermediate directions. They are retained for historical context only.

## Solver research

2. `docs/numerical-optimization-planner-sota.md`
   **SOTA research** for differentiable numerical optimization with gradual
   constraint hardening. Covers Gumbel-Softmax, penalty methods, augmented
   Lagrangian, diffusion models, and differentiable sorting for scheduling.

## Benchmark results

3. `docs/benchmark-results.md`
   **Solver benchmark** comparing greedy, CP-SAT, PyTorch, and fluid solvers
   across all 9 scenarios. Covers correctness, money, blocks, makespan, and
   solve time. Updated July 2026.

## Current scope

- Primary model: **unified entity transformation** with flat key/value properties, QBE matching,
  finite batch semantics, deterministic integer arithmetic, and explicit timed/stateful transitions.
- Matching is QBE by default; restricted `$` expressions are allowed only in whitelisted fields.
- Worker/equipment/tool/material are domain labels, not separate kernel classes.

## How to update docs

1. Update `unified-aps-model.md` first for any semantic change.
2. If the change adds industrial coverage, consider adding an example to the rule catalog in archive.
3. Do not create parallel architecture/spec files; extend the canonical doc instead.