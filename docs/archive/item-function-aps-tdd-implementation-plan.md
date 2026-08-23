# Item-Function APS TDD Implementation and Verification Plan

> Historical implementation/TDD plan for prior execution phase.
> Current architecture decisions and unresolved questions: `docs/item-function-aps-decision-register.md` and `docs/discrete-factory-rule-catalog.md`.

## Purpose

This document converts `docs/item-function-aps-architecture.md` into a step-by-step implementation plan. The goal is to build the Item-Function Universal APS kernel incrementally, with tests leading each slice.

Design priorities, in order:

1. correctness;
2. high performance;
3. function richness;
4. clear structure;
5. extensibility;
6. minimal redundancy and maximal reuse.

## Verification commands

Use the smallest command that covers the changed behavior.

Backend:

```bash
cd backend && uvx ruff check aps/universal tests/test_universal_config.py
cd backend && uv run python -m unittest tests.test_universal_config
```

Add focused test modules as the implementation grows:

```bash
cd backend && uv run python -m unittest tests.test_item_function_schema
cd backend && uv run python -m unittest tests.test_item_function_validation
cd backend && uv run python -m unittest tests.test_item_function_compiler
cd backend && uv run python -m unittest tests.test_item_function_planner
```

Frontend:

```bash
cd frontend && npm run build
cd frontend && npx playwright test tests/universal-aps.spec.js --config=playwright.config.js
```

Add focused browser tests for new UI flows:

```bash
cd frontend && npx playwright test tests/item-function-aps.spec.js --config=playwright.config.js
```

## TDD rules for this effort

1. Write failing tests before implementation for each behavior slice.
2. Keep each slice independently shippable.
3. Prefer deep backend modules with small interfaces.
4. Do not route business logic through API handlers or Vue components.
5. Keep existing Universal APS behavior working while adding the new kernel.
6. Add diagnostics for rejected/unsupported configurations before adding solver features.
7. Validate correctness invariants after every planner result:
   - no negative non-infinite inventory;
   - no overlapping resource usage;
   - no expired lot consumed;
   - locked steps unchanged;
   - objective explanation sums correctly.

## Target package layout

Introduce this package incrementally:

```text
backend/aps/universal/item_function/
  __init__.py
  schema.py
  validation.py
  normalization.py
  tags.py
  selectors.py
  calendars.py
  state_graph.py
  formula.py
  ledger.py
  compiler.py
  planner.py
  diagnostics.py
  samples.py
  ports.py
  adapters/
    __init__.py
    greedy.py
    cpsat.py
```

Initial implementation may omit modules until a test needs them. Avoid placeholder modules with no behavior.

## Phase 0: guardrails and baseline

### Step 0.1: protect current behavior

Failing test first:

- Add/confirm backend tests that current Universal APS templates still list and seed:
  - `discrete_manufacturing`
  - `resource_model_discrete_manufacturing`
  - `discrete_manufacturing_advanced`
  - `batch_process`
  - `fulfillment_center`
  - `job_shop`
- Add/confirm browser test that APS Studio still applies an existing config.

Implementation:

- No behavior change unless tests reveal drift.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_universal_config
cd frontend && npx playwright test tests/universal-aps.spec.js --config=playwright.config.js
```

Acceptance:

- Existing Universal APS behavior stays green before new kernel work starts.

## Phase 1: schema-only item-function kernel

### Step 1.1: define schema test cases

Create `backend/tests/test_item_function_schema.py`.

Failing tests:

1. Valid setup with:
   - `MONEY` objective item;
   - one normal item;
   - one location;
   - one capability;
   - one resource providing that capability;
   - one production path;
   - one order.
2. Reject negative quantities except documented `-1` limit sentinels.
3. Accept `storage_limit = -1`.
4. Reject missing item unit.
5. Reject resource provided capability without `capability_id`.
6. Reject order line without requested item id or quantity.

Implementation:

- Add `schema.py` with Pydantic models:
  - `ItemFunctionSetup`
  - `TagDefinition`
  - `ItemDefinition`
  - `LocationDefinition`
  - `CapabilityDefinition`
  - `ResourceDefinition`
  - `ProvidedCapability`
  - `ProductionPath`
  - `StepDefinition`
  - `OrderDefinition`
  - `InventoryLot`
  - `PlanningProblem`

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_schema
cd backend && uvx ruff check aps/universal/item_function tests/test_item_function_schema.py
```

Acceptance:

- Pydantic catches malformed shapes.
- No semantic cross-reference validation yet.

### Step 1.2: add sample setup generator

Create `backend/tests/test_item_function_samples.py`.

Failing tests:

1. `sample_discrete_manufacturing_setup()` returns schema-valid setup.
2. Sample includes:
   - `MONEY`;
   - raw material item;
   - component item;
   - finished good item;
   - scrap item;
   - machine resource;
   - worker resource;
   - production path;
   - disposal path for scrap.

Implementation:

- Add `samples.py`.
- Keep samples deterministic by seed.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_samples
```

Acceptance:

- Samples are usable by later validation/compiler tests.

## Phase 2: tags and selectors

### Step 2.1: tag taxonomy

Create `backend/tests/test_item_function_tags.py`.

Failing tests:

1. Parent tags expand into child tag matching.
2. Valued tag exact matching works.
3. Exclusive group conflict is detected.
4. Unknown tag references produce diagnostics.
5. Tags normalize to stable sorted representation for inventory stacking.

Implementation:

- Add `tags.py`.
- Add `ValidationDiagnostic` shape if needed.

Interface:

```python
expand_tags(tag_set, taxonomy) -> ExpandedTagSet
validate_tag_set(tag_set, taxonomy) -> list[Diagnostic]
tag_signature(tag_set, taxonomy) -> str
```

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_tags
```

Acceptance:

- Tag behavior is independent of planner/solver.

### Step 2.2: item and resource selectors

Create `backend/tests/test_item_function_selectors.py`.

Failing tests:

1. Inventory selector matches item id, location, tags, and expiry.
2. Selector rejects expired lot at consumption time.
3. Selector rejects forbidden tag.
4. Resource selector matches required capability and tags.
5. Resource selector expands inherited tags.

Implementation:

- Add `selectors.py`.

Interface:

```python
match_inventory(selector, lots, at) -> list[InventoryMatch]
match_resources(selector, resources, taxonomy) -> list[ResourceDefinition]
```

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_selectors
```

Acceptance:

- Matching rules are deterministic and explainable.

## Phase 3: semantic validation and normalization

### Step 3.1: setup validation

Create `backend/tests/test_item_function_validation.py`.

Failing tests:

1. Reject step consuming unknown item.
2. Reject step requiring unknown capability.
3. Reject resource providing unknown capability.
4. Reject order requesting unknown item.
5. Reject production path with invalid batch rule.
6. Reject tag conflict on item/resource/inventory.
7. Warn when no path can produce ordered item.
8. Reject objective item reference if item is missing.

Implementation:

- Add `validation.py`.
- Return structured report:

```python
ValidationReport(
    errors=[Diagnostic(...)],
    warnings=[Diagnostic(...)]
)
```

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_validation
```

Acceptance:

- Invalid business setup fails before planning.
- Reports mention affected entity id and field/path.

### Step 3.2: normalization

Create `backend/tests/test_item_function_normalization.py`.

Failing tests:

1. Inventory lots with identical item/location/expiry/tags stack.
2. Lots with different tags do not stack.
3. `storage_limit = -1` becomes explicit unlimited sentinel internally.
4. Tag inheritance is materialized once.
5. Generated internal ids are stable across runs.

Implementation:

- Add `normalization.py`.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_normalization
```

Acceptance:

- Compiler receives canonical structures, not raw user shapes.

## Phase 4: formula and calendar foundation

### Step 4.1: safe formula parser/evaluator

Create `backend/tests/test_item_function_formula.py`.

Failing tests:

1. Arithmetic formula evaluates deterministically.
2. `ceil`, `floor`, `min`, `max`, `abs`, `round` work.
3. Unknown variable is rejected.
4. Function call outside allowlist is rejected.
5. Attribute access/import/callable execution is rejected.
6. Boolean comparison formula works for eligibility.

Implementation:

- Add `formula.py`.
- Use Python `ast` allowlist or a small expression parser.
- Do not use `eval`.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_formula
```

Acceptance:

- Formula engine is safe and deterministic.

### Step 4.2: calendar expansion

Create `backend/tests/test_item_function_calendars.py`.

Failing tests:

1. Weekly schedule expands to finite windows.
2. Date exception removes a window.
3. Timezone is preserved.
4. Invalid recurrence returns validation diagnostic.
5. Empty calendar means no availability unless explicitly configured as always available.

Implementation:

- Add `calendars.py`.
- Implement minimal RRULE subset:
  - daily;
  - weekly;
  - BYDAY;
  - start/end local time;
  - exclusions.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_calendars
```

Acceptance:

- Solver receives finite time windows.

## Phase 5: inventory ledger

### Step 5.1: planned ledger projection

Create `backend/tests/test_item_function_ledger.py`.

Failing tests:

1. Consuming more than available creates diagnostic.
2. Producing adds inventory at event time.
3. Expired lots cannot satisfy later consumption.
4. Storage limit violation is detected.
5. Infinite `MONEY` inventory can be consumed without going negative.
6. Objective item consumption is summed.
7. Scrap disposal reduces scrap and consumes money.

Implementation:

- Add `ledger.py`.

Interface:

```python
project_ledger(initial_lots, events, setup, horizon) -> LedgerProjection
```

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_ledger
```

Acceptance:

- Ledger can validate a proposed plan without a solver.

## Phase 6: state graph

### Step 6.1: graph validation

Create `backend/tests/test_item_function_state_graph.py`.

Failing tests:

1. Reject edge referencing unknown state.
2. Detect unreachable required state.
3. Accept graph with shortcut edge.
4. Return diagnostic for negative transition duration.

Implementation:

- Add `state_graph.py`.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_state_graph
```

Acceptance:

- Resource state graph errors are caught before planning.

### Step 6.2: transition candidate generation

Extend `test_item_function_state_graph.py`.

Failing tests:

1. Stove example finds path `hot:C -> hot -> warm -> cold -> cold:A`.
2. Shortcut path is included when configured.
3. Pareto frontier keeps fast-expensive and slow-cheap candidates.
4. Candidate limit caps returned alternatives.

Implementation:

- Implement multi-criteria path search.
- Keep Pareto frontier over:
  - duration;
  - objective item cost;
  - required capability count.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_state_graph
```

Acceptance:

- State transition complexity is precomputed before solver creation.

## Phase 7: compiler to canonical planning graph

### Step 7.1: compile simple make scenario

Create `backend/tests/test_item_function_compiler.py`.

Failing tests:

1. One order for finished item compiles to candidate production path.
2. Step has item consumption requirement.
3. Step has capability requirement.
4. Resource candidates are attached by capability.
5. Objective item costs are attached.

Implementation:

- Add `compiler.py`.
- Add canonical graph models either in `schema.py` or `compiler.py`.

Interface:

```python
compile_problem(problem: NormalizedProblem) -> CompiledPlanningGraph
```

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_compiler
```

Acceptance:

- Compiler output is solver-independent.

### Step 7.2: compile buy/outsource/dispose alternatives

Extend compiler tests.

Failing tests:

1. Buy path consumes `MONEY` and produces item.
2. Outsource path consumes `MONEY + material` and produces item.
3. Scrap storage limit creates need for disposal path.
4. Missing disposal path creates diagnostic.
5. Dominated alternatives are pruned.

Implementation:

- Add alternative expansion and dominance pruning.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_compiler
```

Acceptance:

- Make/buy/outsource/dispose are all the same graph primitive.

### Step 7.3: compile movement

Extend compiler tests.

Failing tests:

1. If item is at warehouse and step needs it at line, compiler inserts movement candidate.
2. Movement consumes movement capability.
3. Movement preserves item tags and expiry.
4. Missing movement capability creates diagnostic.

Implementation:

- Treat movement as production path or generated step.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_compiler
```

Acceptance:

- Location constraints are explicit in the compiled graph.

### Step 7.4: compile state transitions

Extend compiler tests.

Failing tests:

1. Required resource state causes transition candidate insertion.
2. Transition consumes configured items.
3. Transition occupies the resource.
4. Unreachable transition creates diagnostic.

Implementation:

- Connect `state_graph.py` output to compiled graph.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_compiler
```

Acceptance:

- Setup/changeover is modeled without hard-coded setup matrices.

## Phase 8: greedy adapter for fast correctness tests

### Step 8.1: define solver seam

Create `backend/tests/test_item_function_planner.py`.

Failing tests:

1. Planner can call a fake adapter and return normalized result.
2. Planner returns validation diagnostics without calling solver when setup invalid.
3. Planner result includes objective explanation.

Implementation:

- Add `ports.py`.
- Add `planner.py`.
- Add `adapters/greedy.py` only when needed.

Interface:

```python
class SolverAdapter(Protocol):
    def solve(self, graph: CompiledPlanningGraph, budget: SolveBudget) -> SolverResult: ...
```

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_planner
```

Acceptance:

- Solver seam is real because fake/greedy adapter and later CP-SAT adapter use same interface.

### Step 8.2: greedy smoke planning

Extend planner tests.

Failing tests:

1. Simple make-from-inventory order schedules.
2. Simple buy-with-money order schedules.
3. Resource intervals do not overlap.
4. Inventory does not go negative.
5. Late order reports lateness penalty.

Implementation:

- Implement deterministic greedy adapter for small examples.
- This adapter is not the final optimizer; it is a correctness harness.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_planner
```

Acceptance:

- Small scenarios can be planned without CP-SAT.

## Phase 9: CP-SAT adapter

### Step 9.1: interval scheduling baseline

Create `backend/tests/test_item_function_cpsat.py`.

Failing tests:

1. Two steps needing same resource do not overlap.
2. Two steps needing different resources may overlap.
3. Precedence is respected.
4. Deadline lateness is calculated.

Implementation:

- Add `adapters/cpsat.py`.
- Lower compiled graph to OR-Tools intervals.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_cpsat
```

Acceptance:

- CP-SAT adapter solves basic finite-capacity scheduling.

### Step 9.2: item balance constraints

Extend CP-SAT tests.

Failing tests:

1. Step cannot consume item before it is produced.
2. Inventory source can satisfy demand without production.
3. Expired lot is not used.
4. Buy path is selected when internal capacity misses deadline.

Implementation:

- Add event-time item availability constraints.
- Use horizon/event approximation first; refine later if needed.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_cpsat
```

Acceptance:

- Item flow and capacity interact in the solver.

### Step 9.3: objective items and alternatives

Extend CP-SAT tests.

Failing tests:

1. Cheaper internal path selected when on time.
2. Expensive buy path selected when internal path is late enough.
3. Scrap disposal is scheduled when scrap storage limit would be exceeded.
4. Objective explanation equals solver objective terms.

Implementation:

- Add optional alternatives and objective item cost terms.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_cpsat
```

Acceptance:

- Solver makes economic tradeoffs using item-consumption objective.

### Step 9.4: state transitions and wait policies

Extend CP-SAT tests.

Failing tests:

1. Required state transition is inserted before production step.
2. No-wait steps start/end adjacent.
3. Bounded wait enforces min/max gap.
4. Fast-expensive transition selected when deadline pressure requires it.

Implementation:

- Add transition candidates as optional intervals.
- Add no-wait/bounded-wait constraints.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_cpsat
```

Acceptance:

- Setup/changeover and inline chains are part of optimization.

## Phase 10: API integration

### Step 10.1: validate endpoint

Extend `backend/tests/test_universal_config.py` or add `test_item_function_api.py`.

Failing tests:

1. `POST /api/universal/configs/{id}/validate` returns item-function diagnostics.
2. Invalid tag conflict returns HTTP 200 with validation errors, not 500.
3. Missing config returns 404.

Implementation:

- Add thin route.
- Route calls `ItemFunctionPlanner.validate_setup`.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_api
```

Acceptance:

- UI can validate config before planning.

### Step 10.2: plan endpoint

Failing tests:

1. `POST /api/universal/configs/{id}/plan` supports `model_kind = item_function_v1`.
2. Existing `discrete_manufacturing_advanced` plan endpoint still works.
3. Invalid item-function setup returns structured 400 detail.
4. Successful response includes:
   - plan steps;
   - item ledger;
   - resource timeline;
   - objective explanation.

Implementation:

- Branch by `model_kind`, not by template name.
- Keep old bridge intact.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_universal_config tests.test_item_function_api
```

Acceptance:

- New kernel is reachable through Universal APS without breaking old templates.

### Step 10.3: auto-realize endpoint

Failing tests:

1. Past plan steps become realized.
2. Future steps remain pending.
3. Realized item effects apply to actual ledger.
4. Re-running auto-realize is idempotent.

Implementation:

- Add plan persistence only as much as this endpoint requires.
- Keep planned and actual ledgers separate.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_api
```

Acceptance:

- Demo execution bridge works without MES.

## Phase 11: frontend integration

### Step 11.1: APS Studio item-function editor shell

Create `frontend/tests/item-function-aps.spec.js`.

Failing browser tests:

1. Item-function template appears in APS Studio.
2. Applying it shows Items/Resources/Locations above pinned Order/Inventory/Plan.
3. APS Studio shows configuration sections:
   - Items;
   - Tags;
   - Locations;
   - Capabilities;
   - Resources;
   - Production paths;
   - State graphs.

Implementation:

- Add UI shell without advanced editors first.

Verification:

```bash
cd frontend && npm run build
cd frontend && npx playwright test tests/item-function-aps.spec.js --config=playwright.config.js
```

Acceptance:

- Users can see and apply the new model.

### Step 11.2: reference/tag-aware editors

Extend browser tests.

Failing tests:

1. Item selector uses item dropdown.
2. Location selector uses location dropdown.
3. Tag picker prevents exclusive-group conflicts.
4. Production step editor can add consume/produce lines.
5. Resource capability editor can add capability/rate/batch capacity.

Implementation:

- Add focused editor components inside existing `App.vue` only as needed.
- Avoid duplicating generic field rendering logic.

Verification:

```bash
cd frontend && npm run build
cd frontend && npx playwright test tests/item-function-aps.spec.js --config=playwright.config.js
```

Acceptance:

- Non-programmers can configure core structures without JSON editing for common cases.

### Step 11.3: plan and diagnostics UI

Failing browser tests:

1. Validate button shows diagnostics.
2. Run Plan shows resource timeline.
3. Run Plan shows item ledger.
4. Infeasible setup shows actionable reason.
5. Auto-realize button shows MES placeholder and realizes elapsed demo plan.

Implementation:

- Add views consuming backend response shape.

Verification:

```bash
cd frontend && npm run build
cd frontend && npx playwright test tests/item-function-aps.spec.js --config=playwright.config.js
```

Acceptance:

- Planner behavior is visible and explainable.

## Phase 12: end-to-end scenario suite

Create backend scenario tests and browser smoke tests for:

1. **Make from stock**
   - Inventory satisfies order directly.
2. **Make from raw material**
   - Raw material consumed, finished good produced.
3. **Buy with money**
   - Money consumed, item receipt planned.
4. **Outsource**
   - Money and material consumed, finished item produced after lead time.
5. **Scrap disposal**
   - Production creates scrap; disposal required by storage limit.
6. **Failed QA rework**
   - Failed item converted to released item or scrap.
7. **Movement**
   - Item moved from warehouse to line before processing.
8. **Expiry**
   - Expired lot ignored; unexpired lot used.
9. **State transition**
   - Stove/machine moves from product C state to product A state.
10. **No-wait/bounded-wait**
    - Inline chain respects time constraints.
11. **Locked replan**
    - Locked future step does not move.
12. **Auto-realize**
    - Past planned steps become actual facts.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_scenarios
cd frontend && npx playwright test tests/item-function-aps.spec.js --config=playwright.config.js
```

Acceptance:

- The architecture works as a user-facing APS, not just isolated modules.

## Phase 13: performance verification

Create `backend/tests/test_item_function_performance.py`.

Performance fixtures:

1. 20 items, 10 resources, 20 orders.
2. 100 items, 50 resources, 100 orders.
3. 300 items, 150 resources, 300 orders.

Tests:

1. Normalization time stays bounded.
2. Compiler alternative counts stay below configured caps.
3. State transition candidate cache avoids repeated graph work.
4. Solver respects configured `max_seconds`.
5. Diagnostics report pruning.

Verification:

```bash
cd backend && uv run python -m unittest tests.test_item_function_performance
```

Acceptance:

- Large configs fail gracefully or solve within budget.
- Performance bottlenecks are visible.

## Phase 14: cleanup and migration hardening

Tests:

1. Old templates still work.
2. New item-function template works.
3. API route code remains thin.
4. No OR-Tools import outside solver adapter and existing legacy planner.
5. No duplicated selector/tag/ledger logic in API/frontend.

Implementation:

- Move any leaked logic back into deep modules.
- Update docs if behavior differs from architecture.

Verification:

```bash
cd backend && uvx ruff check aps/universal tests
cd backend && uv run python -m unittest tests.test_replan_progress tests.test_universal_config tests.test_item_function_schema tests.test_item_function_validation tests.test_item_function_compiler tests.test_item_function_planner
cd frontend && npm run build
cd frontend && npx playwright test tests/universal-aps.spec.js tests/item-function-aps.spec.js --config=playwright.config.js
```

Acceptance:

- The item-function kernel is integrated, tested, explainable, and does not regress the current APS.

## Commit checkpoints

Use commits at meaningful green milestones:

1. schema + samples;
2. tags/selectors/validation;
3. formula/calendar/ledger/state graph;
4. compiler + greedy adapter;
5. CP-SAT adapter baseline;
6. API integration;
7. frontend editor/runtime;
8. E2E scenarios/performance hardening.

Each commit should include only source/test/docs relevant to that milestone. Do not commit local SQLite databases or Playwright result artifacts.

## Definition of done

The Item-Function APS implementation is done when:

1. Users can define items, tags, locations, capabilities, resources, production paths, state graphs, inventory, and orders from APS Studio.
2. Plans can use inventory, make, buy, outsource, move, dispose, rework, and state-transition paths.
3. Objective item consumption is minimized and explained.
4. Infeasible plans produce actionable diagnostics.
5. Replanning respects realized and locked steps.
6. Auto-realize supports demo execution without MES.
7. Existing Universal APS demos still work.
8. Backend tests, static checks, frontend build, and browser tests pass.
