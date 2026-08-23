Here’s a detailed, implementation-oriented APS improvement plan for this codebase, prioritized by business impact and technical dependency.

┌─────────┬───────────┬─────────────────────────────────────────────────────────────────────────────┐
│ Phase   │  Duration │ Primary outcomes                                                            │
├─────────┼───────────┼─────────────────────────────────────────────────────────────────────────────┤
│ Phase 0 │    1 week │ Refactor for extensibility, baseline metrics, scenario persistence skeleton │
├─────────┼───────────┼─────────────────────────────────────────────────────────────────────────────┤
│ Phase 1 │ 2–3 weeks │ Sequence-dependent setup/changeover + richer calendars                      │
├─────────┼───────────┼─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2 │   3 weeks │ Material/inventory/time-phased supply constraints                           │
├─────────┼───────────┼─────────────────────────────────────────────────────────────────────────────┤
│ Phase 3 │ 2–3 weeks │ Order control model (release, priority, partial shipment rules)             │
├─────────┼───────────┼─────────────────────────────────────────────────────────────────────────────┤
│ Phase 4 │   3 weeks │ Alternate routing optimization + lot sizing/splitting                       │
├─────────┼───────────┼─────────────────────────────────────────────────────────────────────────────┤
│ Phase 5 │   2 weeks │ Resource depth (secondary resources, crew constraints)                      │
├─────────┼───────────┼─────────────────────────────────────────────────────────────────────────────┤
│ Phase 6 │   2 weeks │ Replan stability objective + planner controls                               │
├─────────┼───────────┼─────────────────────────────────────────────────────────────────────────────┤
│ Phase 7 │   2 weeks │ APS outputs, diagnostics, scenario compare, integration contracts           │
└─────────┴───────────┴─────────────────────────────────────────────────────────────────────────────┘

1. Phase 0: foundation before feature expansion

1. Split  backend/main.py  into  api.py ,  models.py ,  solver/build_ops.py ,  solver/options.py ,  solver/solve.py ,  metrics.py  without behavior change.
2. Keep  /api/plan  contract stable, add internal version flag to enable new constraints incrementally.
3. Add baseline benchmark set from current test payload patterns plus 3 larger synthetic datasets.
4. Introduce plan persistence tables (scenario, run, blocks, outcomes, input snapshot hash) in SQLite/Postgres (choose one).
5. Define success KPIs: solve success rate, p95 solve time, lateness, cost, schedule-change rate on replan.

2. Phase 1: sequencing realism + calendar fidelity (highest ROI)

1. Add sequence-dependent setup matrix by equipment/task/product-family.
2. Model setup as explicit interval variables on equipment (or transition-time arcs if chosen formulation).
3. Add calendar exceptions: holidays, planned downtime, maintenance windows, date-range shift overrides.
4. Support “campaign mode” (min run length or preferred same-family continuity) with soft penalties.
5. Extend output blocks with  block_type  ( setup|process|maintenance ) and  predecessor_operation_id .
6. Add regression tests: A→B vs B→A changeover asymmetry, holiday crossing, maintenance lockout.

3. Phase 2: material and inventory synchronization

1. Add entities: item, on-hand, safety stock, receipts, purchase/production supply events, reservation policy.
2. Constrain operation start by component material availability timeline, not only precedence graph.
3. Add WIP state support to continue partially completed jobs.
4. Add pegging output: which supply event satisfies each operation/component demand.
5. Introduce infeasibility diagnostics with top blocking materials and earliest feasible dates.
6. Tests: stockout-driven delay, late receipt propagation, pegging consistency.

4. Phase 3: order governance model

1. Extend order model with release date, priority class, customer segment weight, split-allowed flag, min shipment qty.
2. Add weighted tardiness objective terms by priority/customer.
3. Add partial shipment logic with completion milestones and penalties by tranche.
4. Add ATP/CTP-style feasibility check endpoint ( /api/plan/check ) for quick promise queries.
5. Tests: high-priority order preemption behavior, release-date enforcement, split shipment rules.

5. Phase 4: routing optimization + lot-sizing/splitting

1. Replace current fixed/first recipe selection with decision variables over alternate recipes/resources.
2. Add lot-sizing controls: min/max lot, transfer batch, split/merge policy per step.
3. Allow operation overlap rules (downstream can start after transfer batch threshold).
4. Add penalties for excessive splitting to prevent fragmented schedules.
5. Tests: route auto-selection by cost/capacity, split improves lateness but respects min lot.

6. Phase 5: deeper resource constraints

1. Add secondary resources (tools/molds/fixtures) as finite-capacity pools.
2. Add multi-person crew requirements with skill mix constraints.
3. Add certification/qualification constraints with validity date ranges.
4. Add alternative resource groups with preference costs.
5. Tests: tool bottleneck, crew unavailability, certification expiry blocking.

7. Phase 6: replanning stability and control tower behavior

1. Keep  completed_operations  and  locked_operations , plus add  firm_operations  with allowed move windows.
2. Add stability objective: penalties for start-time/resource deviation from previous approved plan.
3. Add freeze fences: near-term horizon no-move except hard violations.
4. Add planner modes:  optimize_cost ,  protect_commitments ,  expedite_priority .
5. Tests: limited nervousness under small demand change, freeze fence respected.

8. Phase 7: APS output quality, diagnostics, and integration

1. Add KPIs: utilization, changeover loss, queue/wait time, OTD, lateness distribution, bottleneck ranking.
2. Add explainability endpoint for unscheduled/infeasible operations with constraint traces.
3. Add scenario/version compare endpoint ( delta lateness/cost/stability ).
4. Define ERP/MES contracts: master data sync, order sync, confirmation feedback, status callbacks.
5. Provide publish workflow: draft → approved → released, with immutable run snapshots.

9. Delivery sequencing (recommended sprint order)

1. Sprint 1: Phase 0.
2. Sprint 2–3: Phase 1.
3. Sprint 4–5: Phase 2.
4. Sprint 6: Phase 3.
5. Sprint 7–8: Phase 4.
6. Sprint 9: Phase 5.
7. Sprint 10: Phase 6.
8. Sprint 11: Phase 7 + hardening.

10. Acceptance gates per phase

1. Functional gate: new constraints represented in input schema, solver, and outputs end-to-end.
2. Quality gate: deterministic regression tests for each new constraint family.
3. Performance gate: p95 solve time regression within agreed budget for benchmark set.
4. Operational gate: infeasibility reasons actionable (not generic “no feasible schedule”).
5. Adoption gate: planner can compare scenario deltas before publish.

If you want, I can convert this into a repo-ready execution backlog with exact API/model fields and CP-SAT variable/constraint design per sprint.
