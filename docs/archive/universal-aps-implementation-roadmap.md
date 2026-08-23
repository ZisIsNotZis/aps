# Universal APS Implementation Roadmap

> Historical roadmap (superseded for current direction).
> Current canonical references: `docs/item-function-aps-decision-register.md` and `docs/discrete-factory-rule-catalog.md`.

## Purpose

This roadmap turns the Universal APS architecture into implementable phases. It is intentionally documentation-only for now. No code should be started until this design is reviewed and accepted.

## Guiding principles

1. Keep the existing planner working throughout.
2. Add a new configuration layer before replacing fixed pages.
3. Prefer deep modules with small interfaces:
   - `FormulaEngine`
   - `ApsCompiler`
   - `SolverAdapter`
   - `DynamicUiSchema`
4. Build template-first, formula-second.
5. Reject unsupported customization early with clear explanations.
6. Track performance with model-size estimates before solve.
7. Version every published configuration.

## Phase 0: Design freeze and terminology

### Outcome

The team agrees on vocabulary and contracts before implementation.

### Deliverables

1. Finalize `Universal APS Architecture`.
2. Create glossary:
   - Concept
   - Field
   - Relationship
   - Constraint
   - Alternative
   - Penalty
   - Goal
   - Formula
   - Template
   - Scenario records
   - Published configuration
   - APS IR
3. Decide initial industry templates:
   - Discrete manufacturing first.
   - Blank expert schema second.
4. Define supported formula functions for v1.
5. Define performance budgets:
   - Max operations.
   - Max assignment options per operation.
   - Max optional intervals.
   - Max solve time for interactive mode.

### Acceptance gate

Architecture docs reviewed and no implementation ambiguity remains for Phase 1.

## Phase 1: Persistence and configuration shell

### Backend

Add persistence for configurations without touching solver behavior.

Target modules:

```text
backend/aps/universal/models.py
backend/aps/universal/persistence.py
backend/aps/universal/api.py
```

Target backend capabilities:

- Create config.
- Read config.
- Patch config.
- Clone config.
- Publish config.
- Store records by concept.
- Clear records.

### Frontend

Add APS Studio navigation entry.

Pages:

- Template selector.
- Concepts list.
- Draft status header.
- JSON preview for debugging.

### Tests

Backend:

- Create draft config.
- Patch draft config.
- Publish immutable version.
- Clone published config.
- Clear records.

Frontend/browser:

- APS Studio opens.
- Template can be selected.
- Draft status is visible.

### Acceptance gate

Users can create and save a draft configuration, but it does not need to solve yet.

## Phase 2: Concept and dynamic record editing

### Backend

Implement concept schema validation.

Field types:

- text
- number
- boolean
- duration
- datetime
- enum
- reference
- multi-reference
- formula, display-only initially

Validation:

- Required fields.
- Unknown fields.
- Duplicate IDs.
- Invalid references.
- Type mismatch.

### Frontend

Dynamic entity editor:

- Render fields from schema.
- Render table columns from schema.
- Add row.
- Edit row.
- Delete row.
- Validate rows.

UX requirement:

- Non-programmers should see labels and help text.
- Expert users can inspect raw JSON.

### Tests

Backend:

- Valid schema accepts records.
- Invalid reference returns actionable validation.
- Required field missing returns concept/field path.

Frontend/browser:

- Add a custom concept.
- Add fields.
- Add records.
- Validation message appears for missing required field.

### Acceptance gate

Users can define custom concepts and edit records without code changes.

## Phase 3: Formula engine v1

### Backend

Create `FormulaEngine` as a deep module.

External interface:

```python
class FormulaEngine:
    def validate(self, formula, context_schema) -> FormulaReport: ...
    def preview(self, formula, records, context_schema) -> FormulaPreview: ...
    def classify(self, formula, context_schema) -> CompileLevel: ...
```

Supported v1:

- Arithmetic.
- Comparisons.
- Boolean operators.
- `min`, `max`, `abs`, `round`, `if`.
- Field references.
- Basic collection aggregations.

Forbidden:

- User-defined functions.
- Imports.
- Attribute access outside schema.
- File/network/process access.

### Frontend

Formula builder:

- Field picker.
- Function picker.
- Expression editor.
- Live validation.
- Sample preview.
- Compile level badge.

### Tests

Backend:

- Formula parses.
- Formula type-checks.
- Formula rejects unknown fields.
- Formula rejects unsafe syntax.
- Formula previews on sample records.

Frontend/browser:

- Enter valid formula and see preview.
- Enter invalid formula and see clear error.

### Acceptance gate

Formulas are safe and useful for validation/derived fields, even before solver compilation.

## Phase 4: Compiler IR v1

### Backend

Create `ApsCompiler`.

External interface:

```python
class ApsCompiler:
    def compile(self, config, records, mode="interactive") -> CompileResult: ...
```

`CompileResult`:

- valid flag
- diagnostics
- IR if valid
- model-size estimate

IR v1 supports:

- Operations.
- Resources.
- Calendars.
- Assignment options.
- Precedence arcs.
- No-overlap constraints.
- Deadline penalties.
- Direct cost objective.

The compiler should first target the existing manufacturing template and generate data equivalent to current `PlanningInput`.

### Frontend

Add Validate and Compile panel:

- Validate schema.
- Validate records.
- Show model-size estimate.
- Show unsupported settings.
- Show generated IR summary.

### Tests

Backend:

- Discrete manufacturing template compiles.
- Invalid relationship blocks compile.
- Model-size estimate matches expected counts.
- Dominated assignment options are pruned.

Frontend/browser:

- Validate config.
- See IR size preview.
- Compile failure shows actionable message.

### Acceptance gate

Default template compiles to IR without solving.

## Phase 5: Solver adapter from IR

### Backend

Create `SolverAdapter`.

External interface:

```python
class SolverAdapter:
    def solve(self, ir, options) -> ScheduleResult: ...
```

This adapter owns OR-Tools construction.

Supported v1:

- Interval variables.
- Optional intervals for assignment alternatives.
- No-overlap by resource.
- Precedence with lags.
- Calendar windows.
- Linear objective terms.

### Compatibility

Keep `/api/plan` working.

Add:

```http
POST /api/universal/configs/{config_id}/solve
```

### Tests

Backend:

- IR solve produces schedule.
- IR solve matches current planner on default template for a small baseline case.
- Infeasible IR returns diagnostics.

### Acceptance gate

The default discrete manufacturing template solves through the new pipeline.

## Phase 6: Data Lab

### Backend

Create schema-aware random data generator.

External interface:

```python
class DataGenerator:
    def generate(self, config, policy, seed) -> GeneratedData: ...
```

Modes:

- simple
- realistic
- stress_test
- intentionally_infeasible

Actions:

- Clear all records.
- Clear generated records.
- Generate data.
- Regenerate with same seed.

### Frontend

Data Lab page:

- Clear data.
- Generate random data.
- Set seed.
- Select realism level.
- Preview generated counts.
- Run quick validate.
- Run quick solve.

### Tests

Backend:

- Same seed produces same data.
- Generated records satisfy required fields.
- Generated relationships are valid.
- Infeasible mode creates expected diagnostic.

Frontend/browser:

- Clear data button requires confirmation.
- Generate data creates rows.
- Same seed is reproducible.

### Acceptance gate

Users can quickly test a configuration without manually entering all data.

## Phase 7: Constraint templates and alternatives

### Backend

Add built-in templates:

- Capacity.
- Calendar availability.
- Precedence.
- Eligibility.
- Material balance.
- Deadline.
- Setup/changeover.
- Certification.
- Alternative route.
- Overtime.
- Freeze fence.

Each template should compile to known IR patterns.

### Frontend

Constraint wizard:

- Pick template.
- Select affected concepts.
- Fill required fields.
- Choose hard/soft.
- See solver impact.
- See example.

Alternatives wizard:

- Candidate set.
- Selection rule.
- Cost impact.
- Duration impact.
- Candidate cap.

### Tests

Backend:

- Each template compiles.
- Each template has at least one infeasibility diagnostic test.
- Alternative fanout caps work.

Frontend/browser:

- Add capacity constraint.
- Add alternative route.
- See compile estimate update.

### Acceptance gate

Most real APS customization can be done through templates, not raw formulas.

## Phase 8: Dynamic planning cockpit

### Backend

Schedule result should include schema-aware display metadata:

- Concept labels.
- Resource labels.
- Operation labels.
- KPI definitions.
- Diagnostic paths back to configured concepts.

### Frontend

Replace fixed planning labels with schema-aware labels.

Dynamic views:

- Schedule timeline.
- KPI cards.
- Diagnostics.
- Bottlenecks.
- Goal contribution.
- Assignment explanation.

### Tests

Frontend/browser:

- Rename Machine to Line and see UI labels update.
- Hide a concept and see navigation update.
- Custom goal appears in result explanation.

### Acceptance gate

Published config changes the main app without code changes.

## Phase 9: Migration from fixed APS to Universal APS

### Migration strategy

1. Represent current hard-coded APS as `discrete_manufacturing_v1` template.
2. Add compatibility adapter:

```text
Current App State -> Template Records -> APS IR
```

3. Keep `/api/plan` as legacy stable route.
4. Make `/api/universal/...` the new route family.
5. Eventually have `/api/plan` call the Universal pipeline with the default template.

### Tests

- Legacy planning still passes current tests.
- Universal default template matches legacy result for representative cases.
- Saved local frontend state can be reset if schema changes.

### Acceptance gate

Users can continue current workflows while testing Universal APS.

## Phase 10: Hardening and enterprise readiness

### Required hardening

- Schema versioning.
- Import/export configuration.
- Audit log for config changes.
- Role permissions:
  - Viewer.
  - Planner.
  - Config editor.
  - Publisher.
- Published config immutability.
- Formula sandbox security tests.
- Model-size protection.
- Documentation and templates.

### Performance checks

Benchmarks:

- Small interactive case.
- Medium production case.
- Large stress case.
- Alternative-heavy case.
- Infeasible case.

Metrics:

- Compile time.
- Solve time.
- IR size.
- CP-SAT variable count.
- CP-SAT constraint count.
- Memory footprint.

### Acceptance gate

Universal APS is safe for non-developer configuration and predictable enough for production pilots.

## Risks and mitigations

### Risk: Users create impossible schemas

Mitigation:

- Guided templates.
- Validation before publish.
- Sample solve before publish.
- Diagnostics with concept and field paths.

### Risk: Formula language becomes programming

Mitigation:

- Template-first UX.
- Formula compile levels.
- Safe expression subset.
- No arbitrary code execution.

### Risk: Solver model explosion

Mitigation:

- Model-size preview.
- Candidate caps.
- Dominance pruning.
- Performance warnings.
- Interactive solve limits.

### Risk: Dynamic UI becomes confusing

Mitigation:

- Guided setup.
- Right-side inspector.
- Industry templates.
- Preview pages.
- Plain-language labels.

### Risk: Current fixed planner gets broken

Mitigation:

- Keep legacy route.
- Add Universal route in parallel.
- Golden tests comparing old and new default template.

## Test strategy summary

Use TDD for each module.

Backend test layers:

1. Formula unit tests.
2. Schema validation tests.
3. Compiler IR tests.
4. Solver adapter tests.
5. API tests.
6. Regression tests comparing legacy and universal default template.

Frontend test layers:

1. Dynamic form rendering.
2. Formula builder interactions.
3. Constraint wizard.
4. Data Lab clear/generate flows.
5. Validate/publish flow.
6. Dynamic planning cockpit labels.

Browser acceptance scenarios:

1. Create a config from template.
2. Add a custom concept.
3. Add fields and records.
4. Add a constraint template.
5. Add a formula penalty.
6. Generate random data.
7. Validate and compile.
8. Solve.
9. Publish.
10. Confirm main app changes labels/pages based on published config.

## First implementation slice recommendation

Start with the smallest vertical slice that proves the architecture:

1. Add APS Studio shell.
2. Add config persistence.
3. Add concepts and records for a minimal job-shop template.
4. Add compiler that emits the existing `PlanningInput` shape.
5. Solve through existing `/api/plan` logic.
6. Show compile diagnostics and random data generation.

This gives immediate user-visible customization without rewriting the solver first.

## Completion definition

The Universal APS implementation is complete when a non-programmer can:

1. Choose an industry template.
2. Rename and add concepts.
3. Add fields and relationships.
4. Configure standard constraints through templates.
5. Add simple formulas for penalties/goals.
6. Clear data.
7. Generate reproducible random data.
8. Validate configuration.
9. Publish configuration.
10. See the main APS app adapt to the published configuration.
11. Run an efficient schedule.
12. Understand diagnostics when a configuration is invalid or infeasible.
