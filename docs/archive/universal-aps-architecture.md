# Universal APS Architecture

> Historical document (superseded for current direction).
> Current canonical references: `docs/item-function-aps-decision-register.md` and `docs/discrete-factory-rule-catalog.md`.

## Purpose

This document defines a target architecture for turning the current APS demo into a configurable "Universal APS" product. The goal is to let a planner or implementation consultant customize concepts, entities, resources, constraints, dependencies, alternatives, penalties, and optimization goals from the UI without editing Python or Vue code for every industry.

The current application is valuable but static: `PlanningInput` in `backend/aps/api.py` has fixed Pydantic models, the solver directly knows those fixed concepts, and `frontend/src/App.vue` renders fixed pages for tasks, resources, equipment, workers, products, inventory, orders, and planning. A Universal APS needs a new seam above that fixed model: users edit a business planning schema, the system validates it, compiles it into a solver-ready intermediate representation, then solves efficiently.

## Design read

Reading this as: expert APS configuration software for manufacturing and adjacent industries, used by planners, consultants, and operations analysts who may not program, with an enterprise cockpit language, leaning toward a guided ontology builder plus a compiler-backed solver engine.

The UI should feel like a professional configuration workbench, not a developer console. The implementation should feel like a compiler pipeline, not a pile of conditional code paths.

## Design alternatives considered

### Alternative A: DSL-first architecture

Users define entities and rules primarily through formulas such as:

```text
operation.required_skill in machine.skills
max(0, order.completion - order.deadline) * order.priority
```

The backend parses these formulas and maps them to solver constraints and objective terms.

Strengths:

- Maximum expressiveness.
- Small backend interface around `validate`, `compile`, `solve`.
- Advanced consultants can model many industries.

Weaknesses:

- Non-programmers can be intimidated.
- Many formulas cannot be compiled efficiently into CP-SAT.
- Error messages become difficult unless the formula language is heavily constrained.

Use this as a power-user layer, not the primary product model.

### Alternative B: ontology-first architecture

Users define business concepts first: Order, Job, Machine, Mold, Worker, Room, Vessel, Truck, Material, Ingredient, Sterilization Batch, Patient Slot, or any other domain-specific entity. Relationships and constraints are configured visually.

Strengths:

- Best non-programmer UX.
- Settings page can be guided and discoverable.
- Concepts can drive dynamic frontend pages, forms, labels, random data, and help text.

Weaknesses:

- Needs a compiler underneath to remain efficient.
- Some advanced solver behavior may be hard to express through simple forms.
- Requires strong templates so users do not start from a blank universe.

Use this as the primary user experience.

### Alternative C: compiler and IR-first architecture

All user configuration is compiled into a strict intermediate representation before solving. The IR contains operation DAGs, resource pools, assignment options, calendars, capacities, precedence arcs, material balance events, optional alternatives, hard constraints, and objective terms.

Strengths:

- Best performance control.
- Clean validation boundary before OR-Tools model creation.
- Lets the system reject slow or non-linear formulas early.
- Supports model-size preview and solver diagnostics.

Weaknesses:

- More backend architecture work.
- Requires schema versioning and migration discipline.
- The UI still needs a user-friendly ontology layer.

Use this as the core engine seam.

## Selected architecture

Use a hybrid:

1. **Ontology-first UI** for non-programmer configuration.
2. **Safe formula layer** for advanced derived fields, eligibility rules, penalties, and goals.
3. **Compiler-backed intermediate representation** for validation, model-size estimates, pruning, and efficient CP-SAT generation.

The deep module should be:

```text
Universal APS Config -> Compiler -> APS IR -> Solver Adapter -> Schedule Result
```

The external interface is small. Most complexity is hidden in validation, formula compilation, IR generation, option pruning, and CP-SAT construction.

## Core module seams

### 1. Configuration Workbench

Owns the user-facing schema:

- Concepts
- Fields
- Relationships
- Constraint templates
- Goal templates
- UI layout
- Formula catalog
- Random data generators

It should not know OR-Tools details.

### 2. Formula Engine

Owns safe expressions:

- Parse
- Type-check
- Unit-check
- Explain
- Evaluate on sample records
- Compile supported formulas into IR terms
- Reject unsupported formulas with actionable messages

It must not execute Python, JavaScript, SQL, or shell commands from users.

### 3. APS Compiler

Owns the conversion from business configuration and records into solver IR.

Responsibilities:

- Resolve concept relationships into operation graphs.
- Expand alternatives into candidate assignments.
- Convert calendars into time windows.
- Convert material rules into supply/demand events.
- Convert hard constraints into IR constraints.
- Convert soft constraints/goals into weighted objective terms.
- Estimate model size before solving.
- Prune dominated alternatives.
- Produce diagnostics before OR-Tools is invoked.

### 4. Solver Adapter

Owns CP-SAT model creation from IR.

Responsibilities:

- Build interval variables.
- Build optional intervals for alternatives.
- Add no-overlap, capacity, calendar, precedence, and material constraints.
- Add linear objective terms.
- Retry horizons.
- Return solver stats, schedule blocks, outcomes, and infeasibility hints.

### 5. Dynamic UI Renderer

Owns rendering entity pages from schema:

- Navigation from configured concepts.
- Forms from field definitions.
- Tables from view definitions.
- Validation messages from backend reports.
- Settings page and guided setup.

It should not hard-code manufacturing-only pages over time.

## Target data contracts

### Universal APS configuration

```json
{
  "id": "factory-default",
  "name": "Factory APS",
  "version": 1,
  "status": "draft",
  "ontology": {
    "concepts": [],
    "relationships": [],
    "constraints": [],
    "goals": []
  },
  "ui_schema": {
    "navigation": [],
    "entity_editors": [],
    "guided_setup_steps": []
  },
  "formula_catalog": {
    "saved_formulas": [],
    "allowed_functions": ["min", "max", "abs", "round", "if", "sum"]
  },
  "sample_data_policy": {
    "seed": 42,
    "realism_level": "simple",
    "row_counts_by_concept": {}
  }
}
```

### Concept definition

```json
{
  "id": "machine",
  "label": "Machine",
  "category": "resource",
  "description": "A finite-capacity production resource.",
  "fields": [
    {
      "id": "code",
      "label": "Code",
      "type": "text",
      "required": true
    },
    {
      "id": "hourly_cost",
      "label": "Hourly Cost",
      "type": "number",
      "unit": "currency/hour",
      "default_value": 0
    }
  ]
}
```

### Relationship definition

```json
{
  "id": "operation-can-run-on-machine",
  "label": "Operation can run on Machine",
  "from_concept_id": "operation",
  "to_concept_id": "machine",
  "cardinality": "many_to_many",
  "meaning": "can_run_on",
  "fields": [
    {
      "id": "duration_hours",
      "label": "Duration Hours",
      "type": "duration",
      "required": true
    }
  ]
}
```

### Constraint definition

```json
{
  "id": "machine-no-overlap",
  "label": "Machine cannot run overlapping operations",
  "type": "no_overlap",
  "severity": "hard",
  "applies_to": ["machine"],
  "template": "finite_capacity_resource",
  "parameters": {
    "capacity_field": "capacity"
  }
}
```

### Formula-backed constraint

```json
{
  "id": "eligible-machine-required",
  "label": "Operation must use an eligible machine",
  "type": "eligibility",
  "severity": "hard",
  "applies_to": ["operation", "machine"],
  "formula": {
    "language": "aps_formula",
    "expression": "machine in operation.eligible_machines",
    "returns": "boolean"
  },
  "compile_hint": "assignment_filter"
}
```

### Goal definition

```json
{
  "id": "minimize-weighted-lateness",
  "label": "Minimize weighted lateness",
  "direction": "minimize",
  "weight": 100,
  "formula": {
    "language": "aps_formula",
    "expression": "max(0, order.completion_hour - order.due_hour) * order.priority_weight",
    "returns": "number"
  },
  "compile_hint": "linear_objective"
}
```

### Intermediate representation

The IR is not edited directly by users.

```json
{
  "schema_hash": "sha256:...",
  "horizon_minutes": 43200,
  "operations": [],
  "resources": [],
  "assignment_options": [],
  "precedence_arcs": [],
  "capacity_constraints": [],
  "calendar_constraints": [],
  "material_events": [],
  "objective_terms": [],
  "diagnostics": [],
  "model_size_estimate": {
    "operations": 0,
    "intervals": 0,
    "optional_intervals": 0,
    "booleans": 0,
    "linear_terms": 0
  }
}
```

## Formula language

### Goals

The formula language should be powerful enough for business users but constrained enough to compile safely.

Allowed formula categories:

1. **Derived fields**
   - `duration_hours = quantity * standard_hours_per_unit`
2. **Eligibility filters**
   - `operation.required_skill in worker.skills`
3. **Soft penalties**
   - `max(0, completion - due) * penalty_per_hour`
4. **Objective terms**
   - `direct_cost + late_penalty - early_bonus`
5. **Visibility and validation**
   - `allow_partial_shipment == true`

Forbidden:

- Loops.
- Recursion.
- Arbitrary function calls.
- File access.
- Network access.
- Python imports.
- JavaScript evaluation.
- Dynamic SQL.

### Supported functions

Initial functions:

- `min(a, b)`
- `max(a, b)`
- `abs(x)`
- `round(x, decimals)`
- `if(condition, then_value, else_value)`
- `sum(collection.field)`
- `count(collection)`
- `exists(collection, predicate)`
- `all(collection, predicate)`
- `any(collection, predicate)`

### Unit system

Every numeric field should optionally carry a unit:

- `hour`
- `minute`
- `currency`
- `currency/hour`
- `quantity`
- `percent`
- `boolean`

The formula engine must reject unit errors:

```text
deadline_hour + machine_code
```

It should suggest fixes:

```text
deadline_hour can only be added to another duration. machine_code is text.
```

### Compile levels

Every formula receives a compile level:

1. `constant`: can be evaluated once.
2. `record_derived`: can be evaluated per record before solving.
3. `assignment_filter`: filters candidate assignment options.
4. `linear_constraint`: compiles to CP-SAT linear constraints.
5. `linear_objective`: compiles to objective terms.
6. `unsupported_for_solver`: valid for display/validation but cannot drive optimization.

The Settings page must show this level so users understand performance.

## Settings page UX

The page should be named **APS Studio** or **Configuration Studio**, not just Settings. It is a workbench for defining how the APS behaves.

### Primary layout

Left navigation:

1. Industry Template
2. Concepts
3. Relationships
4. Constraints
5. Alternatives
6. Penalties and Goals
7. Formulas
8. Pages and Views
9. Data Lab
10. Validate and Publish

Top status strip:

- Active configuration name.
- Draft/published status.
- Schema version.
- Validation status.
- Model-size estimate.

Main panel:

- Guided forms.
- Inline explanations.
- Preview data.
- Validation messages.

Right inspector:

- What this setting means.
- Example.
- Solver impact.
- Common mistakes.

### Industry Template

Users should not start from blank unless they choose "Expert blank schema".

Initial templates:

1. Discrete manufacturing.
2. Process/batch manufacturing.
3. Job shop.
4. Food/pharma batch with expiry and cleaning.
5. Maintenance/work-order scheduling.
6. Field service dispatch.
7. Healthcare slot/resource scheduling.
8. Logistics dock/yard scheduling.

Template selection creates concepts, relationships, constraints, and sample data generator defaults.

### Concepts page

User actions:

- Add concept.
- Rename concept.
- Hide concept from navigation.
- Add field.
- Set field type.
- Mark required.
- Add help text.
- Add reference to another concept.
- Add formula-derived field.
- Preview resulting data page.

Examples:

- Rename "Equipment" to "Machine".
- Add concept "Mold".
- Add concept "Clean Room".
- Add field "Allergen Family" to Product.
- Add field "Temperature Zone" to Storage Area.

### Relationships page

Relationships define structure:

- Product has Workflow Steps.
- Step consumes Material.
- Step can run on Machine.
- Worker has Certification.
- Machine belongs to Work Center.
- Recipe is alternative to Recipe.
- Operation precedes Operation.

The UI should use human sentences:

```text
An Operation can run on many Machines.
Each Machine can run many Operations.
This relationship adds fields: duration, setup family, cost multiplier.
```

### Constraints page

Constraints must be template-first, formula-second.

Built-in templates:

- Resource cannot overlap.
- Resource capacity limit.
- Operation precedence.
- Calendar availability.
- Material availability.
- Eligibility match.
- Minimum/maximum lot size.
- Transfer batch.
- Setup/changeover.
- Cleaning/changeover family.
- Deadline.
- Release date.
- Freeze fence.
- Certification validity.
- Alternative route choice.
- Campaigning/preferred grouping.

Each template should show:

- Plain-language meaning.
- Hard vs soft severity.
- Affected concepts.
- Solver impact.
- Required fields.
- Example failure.

### Alternatives page

Alternative types:

- Alternative machine.
- Alternative worker.
- Alternative recipe.
- Alternative material substitution.
- Alternative operation sequence.
- Optional operation.
- Outsourcing option.
- Overtime option.

Each alternative must have:

- Candidate set.
- Selection rule: one, many, optional.
- Eligibility fields.
- Extra cost/penalty.
- Duration impact.
- Maximum candidate count.

### Penalties and Goals page

Users configure objective profiles here.

Goal types:

- Minimize total cost.
- Minimize weighted lateness.
- Minimize makespan.
- Maximize service level.
- Minimize changeover time.
- Minimize overtime.
- Minimize schedule movement.
- Prefer high-priority orders.
- Prefer campaigns.
- Keep WIP moving.

Each goal should show:

- Weight slider.
- Formula.
- Explanation.
- Example impact.
- Conflict warnings.

Example warning:

```text
High service-level weight and high cost-minimization weight can conflict. The solver will trade off based on weights.
```

### Formula builder

The formula builder should support three modes:

1. **Guided mode**
   - Pick fields and functions from dropdowns.
   - Natural-language preview.
2. **Formula mode**
   - Type `max(0, completion_hour - due_hour) * priority`.
   - Autocomplete fields.
3. **Expert JSON mode**
   - Show underlying config for import/export.

Every formula needs:

- Live parse result.
- Type and unit result.
- Sample evaluation against current/random data.
- Solver compile level.
- Performance warning if it expands many candidates.

### Data Lab

The Data Lab is required for debugging configurations.

Actions:

- Clear all records.
- Clear generated records only.
- Generate random data.
- Generate stress-test data.
- Generate infeasible data intentionally.
- Seed control for reproducibility.
- Validate references.
- Preview compiled IR size.
- Run quick solve.
- Export config and data.
- Import config and data.

Random data generator should be schema-aware:

- It reads concepts and fields.
- It uses relationship cardinality.
- It respects calendars, capacities, and required fields.
- It can intentionally create edge cases.

### Validate and Publish

Publishing should be explicit.

Draft config:

- Editable.
- Can validate.
- Can generate data.
- Can run test solves.

Published config:

- Immutable version.
- Used by normal planning pages.
- Can be cloned into a new draft.

Validation levels:

1. Schema validity.
2. Reference validity.
3. Formula validity.
4. Compiler support.
5. Model-size estimate.
6. Sample solve.

## Backend API sketch

These are target contracts, not implementation for this turn.

```http
GET    /api/universal/configs
POST   /api/universal/configs
GET    /api/universal/configs/{config_id}
PATCH  /api/universal/configs/{config_id}
POST   /api/universal/configs/{config_id}/clone
POST   /api/universal/configs/{config_id}/validate
POST   /api/universal/configs/{config_id}/publish

GET    /api/universal/configs/{config_id}/records/{concept_id}
PUT    /api/universal/configs/{config_id}/records/{concept_id}
POST   /api/universal/configs/{config_id}/records/clear
POST   /api/universal/configs/{config_id}/records/generate

POST   /api/universal/configs/{config_id}/formula/preview
POST   /api/universal/configs/{config_id}/compile
POST   /api/universal/configs/{config_id}/solve
POST   /api/universal/configs/{config_id}/explain
```

## Persistence model

Minimum tables:

- `aps_config`
  - `id`
  - `name`
  - `version`
  - `status`
  - `created_at`
  - `updated_at`
  - `published_at`
  - `schema_json`
  - `schema_hash`

- `aps_config_record`
  - `config_id`
  - `concept_id`
  - `record_id`
  - `record_json`
  - `source`: manual, generated, imported

- `aps_config_validation`
  - `config_id`
  - `schema_hash`
  - `created_at`
  - `report_json`

- `aps_compiled_ir`
  - `config_id`
  - `schema_hash`
  - `data_hash`
  - `created_at`
  - `ir_json`
  - `model_size_json`

- `aps_formula_catalog`
  - `config_id`
  - `formula_id`
  - `formula_json`

Existing scenario tables can later reference a published `schema_hash`.

## Solver efficiency strategy

Full customization can destroy performance unless the compiler controls model shape.

Required controls:

1. **Compile only supported constraints**
   - Reject formulas that cannot become linear constraints/objectives.

2. **Assignment option pruning**
   - Cap candidates by resource, worker, route, and alternative.
   - Remove dominated options where same operation/resource has worse duration and cost.

3. **Model-size preview**
   - Show estimated intervals, optional intervals, booleans, constraints, and objective terms before solve.

4. **Constraint classes**
   - Prefer built-in templates because they compile predictably.
   - Formula constraints need compile hints.

5. **Incremental solving**
   - Cache compiled IR by schema and data hash.
   - Reuse prior plan for stability mode.

6. **Horizon policy**
   - Keep horizon candidate retries, but derive horizons from schema and data.

7. **Fallback diagnostics**
   - If model size exceeds budget, do not blindly solve.
   - Explain which settings caused explosion.

Example diagnostic:

```text
Alternative recipe selection creates 1,920 optional intervals. Reduce candidate machines per step from 40 to 8 or add eligibility filters.
```

## How the current app evolves

### Short term

Keep existing fixed APS pages as the default "Discrete Manufacturing" template. Add APS Studio next to them. APS Studio generates the same shape currently sent to `/api/plan`.

### Medium term

Move fixed pages to schema-driven rendering:

- Tasks becomes a concept page.
- Resources becomes a concept page.
- Equipment becomes a resource concept page.
- Workers becomes a resource concept page.
- Products and workflows become relationship-driven pages.
- Orders becomes a demand concept page.

### Long term

`PlanningInput` becomes a compatibility adapter rather than the primary business model. The true planning contract becomes:

```text
Published Config + Scenario Records -> APS IR -> Schedule Result
```

## Non-goals

- Do not allow arbitrary Python code from users.
- Do not promise every possible business rule can be optimized.
- Do not make the solver accept unbounded formulas.
- Do not remove expert templates. Blank schema is for experts only.
- Do not hide performance impact from users.

## Success criteria

The Universal APS architecture is successful when:

1. A consultant can model a new industry by editing settings, not code.
2. A planner can understand concepts and rules without programming.
3. Formula errors explain what to fix.
4. The compiler predicts model-size problems before solve.
5. Built-in templates remain fast.
6. Random data generation helps users validate configurations quickly.
7. Published configurations are versioned and reproducible.
8. Existing fixed APS behavior can be represented as a default template.
