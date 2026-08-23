# Universal APS Implementation Plan

> Historical implementation plan (superseded for current direction).
> Current canonical references: `docs/item-function-aps-decision-register.md` and `docs/discrete-factory-rule-catalog.md`.

## Scope

This plan converts the Universal APS architecture and roadmap into an execution guide that a weaker model can follow exactly.

The current app is a fixed APS product:

- Backend: `backend/aps/api.py` defines static Pydantic models and solver logic.
- Persistence: `backend/aps/persistence.py` stores scenarios and runs.
- Frontend: `frontend/src/App.vue` renders fixed APS pages and dialogs.

The target is a configuration-first APS where a non-programmer can define:

- concepts
- fields
- relationships
- resources
- constraints
- alternatives
- penalties
- goals
- sample data
- published versions

The app must remain efficient by compiling the user-facing model into a solver-ready IR before OR-Tools.

## Execution rules

1. Keep legacy APS working until Universal APS is proven on a default template.
2. Build the new system as a parallel seam, not a rewrite.
3. Use a deep-module shape:
   - small interface
   - large implementation
4. Prefer template-first UX and safe formulas over arbitrary code.
5. Every phase must end with backend tests, frontend/browser checks, and a measurable acceptance gate.
6. Keep the current default APS template equivalent to the existing fixed behavior wherever possible.
7. Do not begin implementation until each phase below has a written contract and tests.

## Current codebase anchor points

### Backend

- `backend/aps/api.py`
  - fixed planning models
  - `/api/plan`
  - `/api/plan/check`
  - `/api/plan/diagnose`
  - scenario and integration routes
- `backend/aps/persistence.py`
  - scenario persistence
  - versioning
  - baseline snapshot
- `backend/tests/*`
  - all planner regression tests

### Frontend

- `frontend/src/App.vue`
  - all current APS pages
  - modal editors
  - plan cockpit
  - inventory and diagnostics surfaces

### Doc sources

- `docs/universal-aps-architecture.md`
- `docs/universal-aps-implementation-roadmap.md`

## Final product shape

The final system should have two parallel modes:

1. **Legacy APS mode**  
   Current fixed pages, current `/api/plan`, current datasets.

2. **Universal APS mode**  
   A schema-driven APS Studio that edits the planning ontology, validates it, generates sample data, compiles it to APS IR, solves it, and publishes a versioned configuration.

The Universal APS mode should become the default later, but only after it matches or exceeds current behavior.

## Architectural seam to build

The key seam is:

```text
UI configuration -> validated schema -> APS IR -> solver adapter -> result
```

Everything user-editable must compile into that seam.

## Implementation phases

---

## Phase 0: terminology freeze and contract alignment

### Goal

Lock the vocabulary and the first supported customization surface so later phases do not drift.

### Output

A final design contract for:

- `Concept`
- `Field`
- `Relationship`
- `Constraint`
- `Alternative`
- `Penalty`
- `Goal`
- `Formula`
- `Template`
- `Scenario records`
- `Published configuration`
- `APS IR`

### Tasks

1. Freeze the terminology in the architecture doc.
2. Define the first supported industry templates:
   - discrete manufacturing
   - blank expert schema
3. Define supported formula functions for v1:
   - `min`
   - `max`
   - `abs`
   - `round`
   - `if`
   - `sum`
   - `count`
   - `exists`
   - `all`
   - `any`
4. Define solver budgets:
   - max operations per config
   - max assignment options per operation
   - max optional intervals
   - max solve time for interactive mode
5. Define the first public route family:
   - `/api/universal/...`
6. Define compatibility behavior:
   - legacy `/api/plan` must continue to work
   - default Universal APS template must map to current APS behavior

### Files to touch

No code yet. Only docs and planning artifacts.

### Acceptance gate

The team can answer:

- What is a concept?
- What is a field?
- What gets compiled?
- What stays user-facing?
- What is the first supported template?

---

## Phase 1: persistence and configuration shell

### Goal

Add configuration persistence and a visible APS Studio entry without changing solver behavior.

### Backend tasks

1. Create new package:

   ```text
   backend/aps/universal/
   ```

2. Add model definitions for:
   - configuration
   - ontology
   - fields
   - relationships
   - constraints
   - alternatives
   - penalties
   - goals
   - UI schema
   - sample data policy
3. Add persistence for:
   - draft configuration
   - published configuration
   - baseline snapshot
   - schema version
   - schema hash
4. Add configuration CRUD routes:
   - create
   - read
   - patch
   - clone
   - publish
5. Add record storage by concept.
6. Add clear-data actions.

### Frontend tasks

1. Add `APS Studio` navigation entry.
2. Add a shell page for:
   - template selection
   - draft status
   - schema version
   - JSON preview
3. Add visible actions:
   - create draft
   - clone published config
   - publish draft
   - clear data
   - generate random data

### Tests

Backend:

- create draft config
- read config
- patch config
- clone config
- publish config
- clear records

Frontend/browser:

- APS Studio loads
- draft status visible
- template selector visible

### File targets

- `backend/aps/universal/models.py`
- `backend/aps/universal/persistence.py`
- `backend/aps/universal/api.py`
- `frontend/src/App.vue`
- `backend/tests/test_universal_config.py` (new)

### Acceptance gate

A user can create and save a draft configuration, but solving remains unchanged.

---

## Phase 2: concept and dynamic record editing

### Goal

Let users define custom concepts and edit records through schema-driven forms and tables.

### Backend tasks

1. Implement concept validation:
   - duplicate IDs
   - missing required fields
   - invalid references
   - type mismatch
   - unknown fields
2. Support field types:
   - text
   - number
   - boolean
   - duration
   - datetime
   - enum
   - reference
   - multi-reference
   - formula placeholder
3. Add record validation errors with concept/field paths.

### Frontend tasks

1. Render forms from concept schema.
2. Render table columns from concept schema.
3. Add row / edit row / delete row.
4. Show inline validation.
5. Show help text for every field.
6. Allow raw JSON fallback for expert users.

### Tests

Backend:

- valid schema accepts records
- invalid reference fails with readable error
- required field missing reports concept and field

Frontend/browser:

- create custom concept
- add fields
- add records
- observe validation

### File targets

- `backend/aps/universal/models.py`
- `backend/aps/universal/api.py`
- `frontend/src/App.vue`
- `backend/tests/test_universal_schema_validation.py`

### Acceptance gate

Users can define a custom concept and edit data for it without code changes.

---

## Phase 3: safe formula engine v1

### Goal

Allow business-friendly formulas without allowing arbitrary code.

### Backend tasks

1. Create `FormulaEngine` as a deep module.
2. Implement:
   - parse
   - type check
   - unit check
   - sample preview
   - compile-level classification
3. Define allowed syntax only.
4. Reject unsafe syntax.
5. Reject unknown fields.
6. Reject unsupported functions.
7. Return actionable error messages.

### Frontend tasks

1. Add a formula builder with:
   - field picker
   - function picker
   - expression editor
   - live validation
   - preview
   - compile-level badge
2. Support three modes:
   - guided
   - formula
   - expert JSON

### Tests

Backend:

- valid formula parses
- formula preview works
- unknown field rejected
- unsafe syntax rejected
- unit error reported

Frontend/browser:

- valid formula preview visible
- invalid formula shows readable error

### File targets

- `backend/aps/universal/formula_engine.py`
- `backend/aps/universal/api.py`
- `frontend/src/App.vue`
- `backend/tests/test_universal_formula_engine.py`

### Acceptance gate

Formulas work for validation and derived values, but are still bounded and safe.

---

## Phase 4: compiler and intermediate representation v1

### Goal

Compile the user configuration into a solver-neutral APS IR.

### Backend tasks

1. Create `ApsCompiler`.
2. Translate concepts into solver-relevant entities.
3. Expand relationships into:
   - operation DAGs
   - precedence arcs
   - eligibility sets
   - resource constraints
4. Compile built-in constraint templates into IR.
5. Compile soft constraints and goals into objective terms.
6. Produce model-size estimates before solving.
7. Prune dominated assignment options.
8. Produce diagnostics before OR-Tools.

### Frontend tasks

1. Add a compile/validate panel.
2. Show model-size estimate.
3. Show unsupported settings.
4. Show IR summary.
5. Show solver-risk warnings.

### Tests

Backend:

- default discrete manufacturing template compiles
- invalid relationship blocks compile
- model-size estimate reports expected counts
- dominated options are pruned

Frontend/browser:

- compile summary visible
- compile errors are readable

### File targets

- `backend/aps/universal/compiler.py`
- `backend/aps/universal/ir.py`
- `backend/aps/universal/api.py`
- `frontend/src/App.vue`
- `backend/tests/test_universal_compiler.py`

### Acceptance gate

The default template compiles into a stable IR without invoking the solver yet.

---

## Phase 5: solver adapter

### Goal

Solve the compiled IR through OR-Tools without exposing solver internals to the UI layer.

### Backend tasks

1. Create `SolverAdapter`.
2. Build interval variables from IR.
3. Build optional intervals for alternatives.
4. Add no-overlap, precedence, capacity, calendar, and material constraints.
5. Add objective terms.
6. Reuse horizon retries.
7. Return stats, schedule, outcomes, diagnostics.

### Compatibility tasks

1. Keep `/api/plan` operational.
2. Add `/api/universal/configs/{config_id}/solve`.
3. Keep current regression tests green.
4. Ensure default Universal APS template reproduces current legacy behavior closely.

### Tests

Backend:

- solve compiled IR
- infeasible IR returns diagnostics
- default template produces a schedule
- legacy route still works

### File targets

- `backend/aps/universal/solver.py`
- `backend/aps/universal/api.py`
- `backend/aps/api.py` (compatibility hooks only if needed)
- `backend/tests/test_universal_solver.py`

### Acceptance gate

The Universal APS default template can solve end-to-end.

---

## Phase 6: data lab

### Goal

Help users debug a configuration quickly by clearing data or generating random data.

### Backend tasks

1. Create a schema-aware data generator.
2. Support realism modes:
   - simple
   - realistic
   - stress_test
   - intentionally_infeasible
3. Make seed-based generation deterministic.
4. Generate per-concept rows from schema.
5. Respect field types, cardinality, and basic constraints.
6. Add clear-data APIs.

### Frontend tasks

1. Add a Data Lab page.
2. Add actions:
   - clear all data
   - clear generated data
   - generate random data
   - set seed
   - choose realism mode
   - preview generated counts
3. Show reproducibility notes.

### Tests

Backend:

- same seed gives same result
- generated data validates
- intentionally infeasible data triggers expected diagnostics

Frontend/browser:

- clear confirmation works
- generate data populates rows
- same seed repeatable

### File targets

- `backend/aps/universal/generator.py`
- `backend/aps/universal/api.py`
- `frontend/src/App.vue`
- `backend/tests/test_universal_generator.py`

### Acceptance gate

Users can validate a configuration without manual data entry.

---

## Phase 7: built-in constraint templates and alternatives

### Goal

Cover common APS patterns with safe, optimized templates instead of requiring formulas everywhere.

### Backend tasks

1. Add constraint templates for:
   - no overlap
   - finite capacity
   - calendar availability
   - precedence
   - material balance
   - deadline
   - release date
   - setup/changeover
   - certification
   - freeze fence
2. Add alternative templates for:
   - alternate machine
   - alternate worker
   - alternate recipe
   - alternate route
   - overtime
   - outsourcing
3. Add compile hints for each template.

### Frontend tasks

1. Add a constraint wizard.
2. Add an alternatives wizard.
3. Show solver impact and examples per template.
4. Prefer template-first UI over raw formula authoring.

### Tests

Backend:

- each template compiles
- each template has at least one diagnostic test
- alternative fanout caps work

Frontend/browser:

- add capacity constraint
- add alternative route
- see model estimate change

### File targets

- `backend/aps/universal/constraints.py`
- `backend/aps/universal/alternatives.py`
- `backend/aps/universal/api.py`
- `frontend/src/App.vue`
- `backend/tests/test_universal_constraint_templates.py`

### Acceptance gate

Most common APS customization can be expressed through templates.

---

## Phase 8: dynamic planning cockpit

### Goal

Make the main planning UI adapt to the published configuration.

### Backend tasks

1. Return schema-aware labels in solver results.
2. Return concept-linked diagnostics.
3. Return schema-linked KPI definitions.
4. Return configuration version hash with results.

### Frontend tasks

1. Render pages from published schema.
2. Rename labels based on concepts.
3. Hide unused concepts.
4. Show dynamic navigation.
5. Show config-aware KPI cards.
6. Keep planning, diagnostics, and integration surfaces but map them to schema concepts.

### Tests

Frontend/browser:

- rename Machine to Line and see labels update
- hide a concept and confirm navigation changes
- custom goal appears in explanation

### File targets

- `backend/aps/universal/api.py`
- `frontend/src/App.vue`
- `backend/tests/test_universal_dynamic_ui.py`

### Acceptance gate

Published config changes the main app without code edits.

---

## Phase 9: migration from fixed APS to Universal APS

### Goal

Move the current app onto the new architecture without breaking users.

### Tasks

1. Encode the current fixed APS as the default discrete manufacturing template.
2. Map legacy `PlanningInput` to Universal APS config + records.
3. Keep `/api/plan` as a compatibility route.
4. Add new Universal APS routes in parallel.
5. Compare legacy vs universal outputs on baseline cases.
6. Gradually migrate current pages to schema-driven rendering.

### Tests

- legacy planner tests stay green
- default universal template matches current baseline behavior
- scenario and integration features still work

### Acceptance gate

Users can continue current workflows while Universal APS expands.

---

## Phase 10: hardening and enterprise readiness

### Goal

Make the system safe for real customer configuration work.

### Tasks

1. Add schema versioning.
2. Add import/export for configurations.
3. Add audit logging.
4. Add publish immutability.
5. Add roles:
   - viewer
   - planner
   - config editor
   - publisher
6. Add solver performance budgets and warnings.
7. Add benchmark datasets.
8. Add docs and starter templates.

### Tests

- config versioning works
- import/export round-trip works
- published config is immutable
- formula sandbox cannot escape
- model-size warnings trigger correctly

### Acceptance gate

The Universal APS is safe enough for a production pilot.

---

## File plan

### New backend package

```text
backend/aps/universal/
  __init__.py
  api.py
  models.py
  persistence.py
  formula_engine.py
  compiler.py
  ir.py
  solver.py
  generator.py
  constraints.py
  alternatives.py
```

### New tests

```text
backend/tests/test_universal_config.py
backend/tests/test_universal_schema_validation.py
backend/tests/test_universal_formula_engine.py
backend/tests/test_universal_compiler.py
backend/tests/test_universal_solver.py
backend/tests/test_universal_generator.py
backend/tests/test_universal_constraint_templates.py
backend/tests/test_universal_dynamic_ui.py
```

### Frontend

The first implementation should keep changes localized to:

```text
frontend/src/App.vue
```

Only later should the UI be split into dedicated components.

### Docs

```text
docs/universal-aps-architecture.md
docs/universal-aps-implementation-roadmap.md
docs/universal-aps-implementation-plan.md
```

## Dependency order

1. Term glossary and contract freeze.
2. Persistence shell.
3. Concept schema validation.
4. Formula engine.
5. Compiler IR.
6. Solver adapter.
7. Data Lab.
8. Constraint templates.
9. Dynamic cockpit.
10. Migration.
11. Hardening.

Do not skip steps. Later phases depend on earlier seams.

## Testing order

For every phase:

1. Add backend tests first.
2. Add frontend/browser tests second.
3. Implement the minimal code to pass those tests.
4. Add one regression test for the failure mode that motivated the work.
5. Re-run the smallest relevant static check.

## Acceptance checklist for each phase

Each phase is only done when:

- the documented file targets are identified
- the backend contract is written down
- the frontend interaction is written down
- tests are named and scoped
- acceptance gates are explicit
- rollback or compatibility story is clear

## Suggested implementation sprint order

### Sprint 1

- Phase 0
- Phase 1 backend shell

### Sprint 2

- Phase 1 frontend shell
- Phase 2 schema validation

### Sprint 3

- Phase 2 dynamic record editing
- Phase 3 formula engine foundation

### Sprint 4

- Phase 3 formula builder UI
- Phase 4 compiler IR

### Sprint 5

- Phase 5 solver adapter
- baseline compatibility tests

### Sprint 6

- Phase 6 data lab

### Sprint 7

- Phase 7 constraint templates

### Sprint 8

- Phase 8 dynamic planning cockpit

### Sprint 9

- Phase 9 migration work

### Sprint 10

- Phase 10 hardening
- benchmark and security pass

## Risks and mitigations

### Risk: users create impossible schemas

Mitigation:

- guided templates
- compile-time validation
- model-size estimate
- sample solve before publish

### Risk: formula language becomes programming

Mitigation:

- safe expression subset only
- no imports
- no loops
- no arbitrary code execution

### Risk: model explodes

Mitigation:

- fanout caps
- dominated option pruning
- compile warnings
- hard budgets

### Risk: current APS behavior regresses

Mitigation:

- keep compatibility route
- compare default template results with current baseline
- migrate gradually

### Risk: UI becomes too complex

Mitigation:

- template-first wizards
- help text
- inspector panel
- raw JSON only for experts

## Completion definition

Universal APS implementation is complete when a non-programmer can:

1. choose a template
2. rename or add concepts
3. define fields and relationships
4. add constraints and goals
5. add formulas safely
6. clear data
7. generate random data
8. validate the config
9. publish a version
10. run a solve
11. understand diagnostics
12. use the main APS app with schema-driven labels and pages
