# Universal APS Rich Runtime Audit and Execution Plan

> Historical runtime audit/plan (partially superseded).
> Current canonical references: `docs/item-function-aps-decision-register.md` and `docs/discrete-factory-rule-catalog.md`.

## Purpose

This plan converts the latest Universal APS critique into an exact implementation guide. It is intentionally written before coding. The goal is to move from the current shallow schema-driven CRUD prototype to a configurable APS runtime where applied configurations produce operational pages that feel hand-built, remain as function-rich as the fixed production example, and can still be customized from APS Studio.

## Current audit evidence

### Visual evidence captured

Screenshots were captured with Playwright against the local hot-reload app:

- `/home/z/.copilot/session-state/adf66ce9-28cf-445e-8359-7d08ab341310/files/universal-audit-studio.png`
- `/home/z/.copilot/session-state/adf66ce9-28cf-445e-8359-7d08ab341310/files/universal-audit-applied-resource.png`
- `/home/z/.copilot/session-state/adf66ce9-28cf-445e-8359-7d08ab341310/files/universal-audit-applied-equipment.png`

The captured applied configuration navigation for Discrete Manufacturing is:

```text
Resource, Equipment, Worker, Product, Order, APS Studio, Plan
```

The applied Equipment page only exposes:

```text
Code, Name, Availability
```

The applied Resource page only exposes:

```text
Code, Name, Base price / hour
```

This proves the current Universal pages are generic concept CRUD, not rich APS pages.

### Code evidence

Current applied navigation in `frontend/src/App.vue` is driven directly from `payload.concepts`:

```js
return [...conceptNavItems.value, { key: "studio", label: "APS Studio" }, { key: "plan", label: "Plan" }];
```

Current applied concept rendering in `frontend/src/App.vue` is one generic table and one generic form:

```vue
<input
  v-if="field.type !== 'boolean'"
  v-model="conceptEditor.draft[field.id]"
  :type="field.type === 'number' ? 'number' : 'text'"
/>
```

This means `reference`, `multi-reference`, `enum`, workflow, BOM, calendars, matrices, and nested lines currently degrade into text or number inputs.

The fixed APS modal code in `frontend/src/App.vue` already has richer hand-written widgets for:

- Resource hourly price bands.
- Equipment task-hour and resource-usage matrix.
- Equipment weekly availability.
- Product workflow steps.
- Assembly component rows.
- Worker skills.
- Worker availability and overtime windows.
- Order service class, partial shipment controls, and product/recipe line selectors.

The fixed backend models in `backend/aps/api.py` include rich planning fields that the current Universal templates do not fully represent:

- `ResourceDefinition.hourly_prices`
- `EquipmentDefinition.efficiencies`
- `EquipmentDefinition.resource_usage_per_hour`
- `EquipmentDefinition.idle_cost_per_hour`
- `EquipmentDefinition.power_on_time_hour`
- `EquipmentDefinition.power_off_time_hour`
- `EquipmentDefinition.setup_transitions`
- `EquipmentDefinition.calendar_exceptions`
- `EquipmentDefinition.availability`
- `WorkerDefinition.skills`
- `WorkerDefinition.work_cost_per_hour`
- `WorkerDefinition.idle_cost_per_hour`
- `WorkerDefinition.commute_in_time_hour`
- `WorkerDefinition.commute_out_time_hour`
- `WorkerDefinition.certifications`
- `WorkerDefinition.calendar_exceptions`
- `WorkerDefinition.availability`
- `WorkerDefinition.allow_overtime`
- `WorkerDefinition.overtime_cost_multiplier`
- `WorkerDefinition.overtime_availability`
- `ProductDefinition.workflow`
- `ProductDefinition.recipes`
- `WorkflowStep.yield_rate`
- `WorkflowStep.scrap_rate`
- `WorkflowStep.transfer_time_hour`
- `WorkflowStep.queue_buffer_hour`
- `WorkflowStep.required_tools`
- `WorkflowStep.required_certifications`
- `WorkflowStep.required_crew_size`
- `WorkflowStep.assemble_components`
- `OrderDefinition.release_hour`
- `OrderDefinition.deadline_hour`
- `OrderDefinition.penalty_per_hour`
- `OrderDefinition.pre_deadline_bonus_per_hour`
- `OrderDefinition.priority_weight`
- `OrderDefinition.service_class`
- `OrderDefinition.allow_partial_shipment`
- `OrderDefinition.minimum_shipment_quantity`
- `OrderDefinition.partial_shipment_milestone_hour`
- `OrderDefinition.lines`
- `PlanningInput.initial_inventory`
- `PlanningInput.safety_stock_by_product`
- `PlanningInput.inventory_reservations`
- `PlanningInput.inventory_receipts`
- `PlanningInput.completed_operations`
- `PlanningInput.locked_operations`
- `PlanningInput.prior_operations`
- `PlanningInput.mode`
- `PlanningInput.objective_profile`
- `PlanningInput.freeze_fence_hour`
- `PlanningInput.stability_move_penalty_per_hour`

## Design read

Universal APS is not a generic database builder. It is an enterprise operations cockpit and model workbench for planners, implementation consultants, and analysts. The correct UI style is dense, structured, and operational. The UI/UX skill search recommends a data-dense dashboard style: high information visibility, strong tables, clear filtering, visible focus states, compact spacing, and subtle motion only.

The core product rule is:

```text
APS Studio configures the system; applied configs must render as usable APS applications, not raw schema editors.
```

## Main diagnosis

### Problem 1: concepts are being treated as pages

The current runtime uses each concept as a sidebar page. This works for a prototype, but real APS pages are business workspaces, not tables for raw concepts. A manufacturing "Equipment" page needs capability matrix, setup transitions, calendars, costs, and downtime. A fulfillment "Orders" page needs demand lines, SKU selection, promise windows, wave eligibility, and shipment status.

### Problem 2: field types are too weak

Current field metadata only supports simple primitives plus undeveloped `reference` and `multi-reference` hints. It lacks renderer intent, validation intent, units, lookup labels, nested collection schemas, matrix axes, formulas, derived values, conditional visibility, and page placement.

### Problem 3: references are not validated or rendered as lookups

Reference fields such as `batch.recipe_code`, `shipment.wave_id`, and `operation.job_id` should be dropdowns or comboboxes using target concept records. Today they render as text inputs, which lets users create broken links.

### Problem 4: common APS surfaces disappeared after applying configs

The fixed app has Inventory and Orders as first-class pages. After applying Discrete Manufacturing, Inventory disappears because the current template lacks a concept/page for it. Across industries, every APS still needs some form of demand and supply availability:

- Discrete manufacturing: orders, inventory, receipts, reservations, safety stock.
- Batch process: batches, shipments, ingredients/material inventory, quality holds.
- Fulfillment: shipments/orders, SKU inventory, waves, dock capacity.
- Job shop: jobs/customer orders, material availability, WIP, due dates.

The labels and widgets vary, but the planning concerns remain.

### Problem 5: old fixed production example is not representable

The current Discrete Manufacturing template has only five shallow concepts. It cannot encode the fixed app's rich production model because it lacks field types for weekly calendars, hourly price bands, workflow steps, recipes, BOM/component assembly, capability matrices, resource consumption matrices, setup transitions, downtime, worker overtime, certifications, material reservations, receipts, objective profiles, freeze fences, and replan stability.

### Problem 6: Universal records do not compile to planning

The Plan page still runs `buildPayload()` from legacy in-memory fixed arrays. Applying a Universal config changes navigation, but it does not yet make Universal records the source of `/api/plan`, `/api/plan/check`, or `/api/plan/diagnose`.

## Target architecture correction

Keep the existing parallel-seam strategy, but add one missing runtime layer:

```text
Universal Config
  -> Page Blueprints
  -> Field Renderers
  -> Validated Records
  -> Planning Adapter / Compiler
  -> Existing PlanningInput or future APS IR
  -> Solver
```

For the next implementation slice, compile the advanced manufacturing Universal template into the existing `PlanningInput`. Do not build a new general CP-SAT IR yet. This gives an immediate proof that APS Studio can reproduce the current fixed production example.

## Required schema additions

### 1. Core app shell metadata

Add a top-level `app_schema` or extend `ui_schema` with:

```json
{
  "navigation": [
    { "id": "resources", "label": "Resources", "kind": "page", "page_id": "resources" },
    { "id": "equipment", "label": "Equipment", "kind": "page", "page_id": "equipment" },
    { "id": "workers", "label": "Workers", "kind": "page", "page_id": "workers" },
    { "id": "products", "label": "Products", "kind": "page", "page_id": "products" },
    { "id": "inventory", "label": "Inventory", "kind": "page", "page_id": "inventory" },
    { "id": "orders", "label": "Orders", "kind": "page", "page_id": "orders" }
  ],
  "pinned_pages": ["studio", "plan"]
}
```

Do not derive navigation directly from concepts. Derive navigation from page blueprints. Concepts are data model parts; pages are UX workspaces.

### 2. Page blueprints

Add `ui_schema.pages[]` entries that describe:

- page id
- label
- primary concept
- table columns
- summary cards
- editor sections
- field layout
- empty state
- create button label
- supported actions

Example:

```json
{
  "id": "equipment",
  "label": "Equipment",
  "primary_concept": "equipment",
  "template": "capability_matrix_page",
  "table": {
    "columns": ["code", "name", "idle_cost_per_hour", "availability_summary"]
  },
  "editor": {
    "sections": [
      { "title": "Identity", "fields": ["code", "name"] },
      { "title": "Cost and startup", "fields": ["idle_cost_per_hour", "power_on_time_hour", "power_off_time_hour"] },
      { "title": "Task capability matrix", "fields": ["efficiencies", "resource_usage_per_hour"] },
      { "title": "Setup transitions", "fields": ["setup_transitions"] },
      { "title": "Availability", "fields": ["availability", "calendar_exceptions"] }
    ]
  }
}
```

### 3. Rich field kinds

Support these field kinds before adding more industries:

| Field kind | Purpose | Required renderer |
| --- | --- | --- |
| `text` | Codes, names, labels | text input |
| `number` | Numeric scalar | number input with min/max/step/unit |
| `boolean` | Toggle behavior | select/toggle |
| `enum` | Closed list | select |
| `reference` | Link to one record | combobox/select from target concept |
| `multi_reference` | Link to many records | multi-select/chips |
| `record_list` | Nested rows | inline table editor |
| `weekly_calendar` | Repeating availability | day/start/end row editor |
| `calendar_exceptions` | Dated/week exceptions | row editor |
| `hourly_price_bands` | Daily price bands | start/end/price row editor |
| `task_skill_matrix` | worker-task capability | task dropdown + multiplier rows |
| `equipment_capability_matrix` | equipment-task speed and resource usage | matrix with task rows and resource columns |
| `workflow_steps` | product process routing | ordered step cards |
| `bom_components` | assembly dependencies | product reference + quantity rows |
| `order_lines` | demand lines | product/recipe dropdown + quantity/lot controls |
| `setup_transitions` | sequence-dependent setup | from task/to task/time/cost rows |
| `formula` | safe calculated value or penalty | formula editor with validation |

Field definitions must include renderer metadata, not just storage type:

```json
{
  "id": "product",
  "label": "Product",
  "type": "reference",
  "reference": {
    "concept": "product",
    "value_field": "code",
    "label_template": "{{code}} - {{name}}"
  },
  "required": true
}
```

### 4. Validation metadata

Each field should support:

- `required`
- `default`
- `min`
- `max`
- `step`
- `unit`
- `help_text`
- `placeholder`
- `visible_when`
- `readonly_when`
- `options`
- `reference`
- `item_schema`

### 5. Common APS page categories

Every non-blank template should declare these logical page categories, even when labels differ:

| Category | Manufacturing label | Batch label | Fulfillment label | Job shop label |
| --- | --- | --- | --- | --- |
| `capacity_resources` | Equipment | Tanks/Lines | Zones/Docks/Pickers | Machines |
| `labor_resources` | Workers | Operators | Pickers | Operators |
| `process_definitions` | Products/Recipes | Recipes | SKU handling rules | Routings |
| `demand` | Orders | Shipments/Batches | Orders/Shipments/Waves | Jobs |
| `inventory_supply` | Inventory | Ingredients/WIP | SKU Inventory | Material/WIP |
| `planning_controls` | Policies | Campaign rules | Wave policies | Dispatch rules |
| `studio` | APS Studio | APS Studio | APS Studio | APS Studio |
| `plan` | Plan | Plan | Plan | Plan |

## Advanced manufacturing template requirements

Add a new template named `discrete_manufacturing_advanced`. It must represent the fixed app's current data model exactly enough to compile into `PlanningInput`.

### Required concepts

1. `task_type`
2. `resource`
3. `equipment`
4. `worker`
5. `tool_pool`
6. `product`
7. `recipe`
8. `workflow_step`
9. `workflow_component`
10. `order`
11. `order_line`
12. `inventory_item`
13. `inventory_receipt`
14. `inventory_reservation`
15. `calendar_window`
16. `calendar_exception`
17. `setup_transition`
18. `planning_policy`
19. `completed_operation`
20. `locked_operation`
21. `prior_operation`

### Required pages

1. Tasks
2. Resources
3. Equipment
4. Workers
5. Products
6. Inventory
7. Orders
8. Policies
9. APS Studio
10. Plan

### Required page behavior

Reuse the UX patterns from the fixed app:

- Equipment page must include a task-hour and resource-usage matrix.
- Worker page must include skill rows, certifications, weekly availability, and overtime availability.
- Product page must include workflow steps, recipes, and assembly components.
- Inventory page must include initial stock, safety stock, reservations, and receipts.
- Order page must include line-item product/recipe dropdowns, release/deadline hours, priority, service class, partial shipment controls, lateness penalty, and earliness bonus.
- Resource page must include base price and hourly price bands.
- Plan page must run against records from the applied Universal config.

### Required compiler mapping

Implement a backend adapter:

```text
Universal config + universal records -> PlanningInput
```

For `discrete_manufacturing_advanced`, the adapter must map:

| Universal concept | PlanningInput field |
| --- | --- |
| `resource` | `resources[]` |
| `tool_pool` | `tool_pools[]` |
| `equipment` | `equipments[]` |
| `worker` | `workers[]` |
| `product` + `recipe` + `workflow_step` | `products[]` |
| `order` + `order_line` | `orders[]` |
| `inventory_item.on_hand_qty` | `initial_inventory` |
| `inventory_item.safety_stock_qty` | `safety_stock_by_product` |
| `inventory_receipt` | `inventory_receipts[]` |
| `inventory_reservation` | `inventory_reservations[]` |
| `completed_operation` | `completed_operations[]` |
| `locked_operation` | `locked_operations[]` |
| `prior_operation` | `prior_operations[]` |
| `planning_policy` | `mode`, `objective_profile`, `freeze_fence_hour`, `stability_move_penalty_per_hour`, `optimize_alternate_routing` |

The compiler must validate all references before constructing `PlanningInput`.

## Frontend implementation plan

### Phase F1: create schema renderer helpers without replacing current pages

Files:

- `frontend/src/App.vue`

Tasks:

1. Add computed maps:
   - `recordsByConcept`
   - `recordsByConceptAndKey`
   - `conceptById`
   - `fieldByConceptAndId`
   - `activePageBlueprint`
2. Add helper:
   - `fieldValueLabel(field, value)`
   - `referenceOptions(field)`
   - `normalizeUniversalFieldType(field)`
3. Add renderer dispatch functions:
   - `isTextField`
   - `isNumberField`
   - `isBooleanField`
   - `isEnumField`
   - `isReferenceField`
   - `isMultiReferenceField`
   - `isRecordListField`
   - `isWeeklyCalendarField`
   - `isMatrixField`
4. Do not remove legacy fixed pages.

Acceptance:

- Existing fixed app still builds.
- Applied simple configs still show pages.
- Reference and enum metadata can be inspected in Vue without errors.

### Phase F2: navigation from page blueprints

Files:

- `frontend/src/App.vue`

Tasks:

1. Change Universal applied navigation from concepts to `payload.ui_schema.pages`.
2. Keep `APS Studio` and `Plan` pinned at the end.
3. If a config has no page blueprints, fall back to concept pages for compatibility.
4. Add page category labels in subtitles, not generic "Schema-driven resource page".

Acceptance:

- Applying Discrete Manufacturing Advanced shows Tasks, Resources, Equipment, Workers, Products, Inventory, Orders, Policies, APS Studio, Plan.
- Applying Job Shop still shows Jobs/Operations/Machines/Operators plus common demand/inventory pages if its template declares them.
- No applied config loses Plan or APS Studio.

### Phase F3: reference and enum fields

Files:

- `frontend/src/App.vue`
- `frontend/tests/universal-aps.spec.js`

Tasks:

1. Render `enum` as select from `field.options`.
2. Render `reference` as select/combobox from target concept records.
3. Render `multi_reference` as multi-select or checkbox list.
4. Display reference labels in tables instead of raw IDs when possible.
5. Disable create/save when required reference has no target options and show a clear helper message.

Acceptance:

- Batch `batch.recipe_code` renders as a Recipe dropdown.
- Fulfillment `shipment.wave_id` renders as a Wave dropdown.
- Job shop `operation.job_id` renders as a Job dropdown.
- Playwright verifies no reference field appears as a plain text input.

### Phase F4: rich page templates

Files:

- `frontend/src/App.vue`

Tasks:

1. Implement a generic `richEditor` section renderer inside the existing file.
2. Support these page templates:
   - `simple_table_page`
   - `resource_pricing_page`
   - `capability_matrix_page`
   - `worker_skills_page`
   - `product_workflow_page`
   - `inventory_balance_page`
   - `order_demand_page`
   - `planning_policy_page`
3. Reuse existing fixed-page modal row patterns as the visual reference.
4. Keep implementation surgical: add helper functions and conditional template blocks, do not rewrite `App.vue`.

Acceptance:

- Applied advanced manufacturing Equipment page visually exposes matrix, setup, costs, and calendars.
- Applied advanced manufacturing Order page visually exposes order lines with product/recipe selects.
- Applied advanced manufacturing Inventory page visually exposes stock, safety stock, reservations, and receipts.
- UI no longer shows Record ID as a primary operational column unless page blueprint asks for it.

### Phase F5: Universal Plan binding

Files:

- `frontend/src/App.vue`

Tasks:

1. When `universalAppliedConfigId` is set and template supports planning adapter, Run Plan should call a Universal compile-and-plan endpoint instead of legacy `buildPayload()`.
2. Plan Check and Diagnose should use the same source.
3. Keep legacy `buildPayload()` path for no applied config.
4. Surface compiler validation errors in the Plan cockpit.

Acceptance:

- Running Plan after applying Discrete Manufacturing Advanced uses Universal records.
- Broken references produce user-visible validation errors before solver invocation.
- Legacy static mode still runs.

## Backend implementation plan

### Phase B1: formal schema models

Files:

- `backend/aps/universal/models.py`
- `backend/tests/test_universal_config.py`

Tasks:

1. Add typed models for:
   - `UniversalFieldDefinition`
   - `UniversalReferenceDefinition`
   - `UniversalPageDefinition`
   - `UniversalPageSection`
   - `UniversalTableDefinition`
   - `UniversalValidationRule`
2. Keep `payload` stored as dict for migration flexibility, but validate templates before returning them.
3. Add normalization aliases:
   - accept both `multi-reference` and `multi_reference`
   - emit one canonical form, preferably `multi_reference`

Acceptance:

- Existing templates validate.
- New advanced template validates.
- API response shape remains backward compatible.

### Phase B2: record validation

Files:

- `backend/aps/universal/api.py`
- `backend/aps/universal/persistence.py`
- `backend/aps/universal/models.py`
- `backend/tests/test_universal_config.py`

Tasks:

1. Before create/update record, load config and validate:
   - concept exists
   - required fields exist
   - number fields are numeric
   - enum values are allowed
   - references point to existing target records by configured key
   - nested row fields validate recursively
2. Return HTTP 400 with actionable details.
3. Do not silently drop unknown fields; either preserve them only if `allow_extra_fields` is true or reject them.

Acceptance:

- Creating an operation with unknown job reference fails.
- Creating a batch with valid recipe reference succeeds.
- Creating a required field as empty fails.

### Phase B3: advanced manufacturing template and seed data

Files:

- `backend/aps/universal/models.py`
- `backend/tests/test_universal_config.py`

Tasks:

1. Add `discrete_manufacturing_advanced` template.
2. Add demo config named `Discrete Manufacturing Advanced Demo`.
3. Generate records that cover:
   - at least 4 task types
   - at least 3 resources with hourly price bands
   - at least 4 equipment records with task/resource matrices
   - at least 5 workers with skills, calendars, and overtime variations
   - at least 4 products with workflows
   - at least 1 assembled product with BOM components
   - at least 8 orders with multi-line demand
   - inventory for products/components
   - receipts and reservations
   - one planning policy
4. Data must be deterministic by seed.

Acceptance:

- Generated data has enough references to exercise dropdowns.
- Generated data compiles to `PlanningInput`.
- Generated data can run `/api/plan` through the adapter.

### Phase B4: Universal planning adapter

Files:

- `backend/aps/universal/planning_adapter.py`
- `backend/aps/universal/api.py`
- `backend/tests/test_universal_planning_adapter.py`

Tasks:

1. Add `build_planning_input(config, records) -> PlanningInput`.
2. Support only `discrete_manufacturing_advanced` first.
3. Validate references and raise a typed validation error with paths.
4. Add routes:
   - `POST /api/universal/configs/{config_id}/plan`
   - `POST /api/universal/configs/{config_id}/plan/check`
   - `POST /api/universal/configs/{config_id}/plan/diagnose`
5. Internally call existing:
   - `plan_advanced_schedule`
   - `plan_capacity_check`
   - `diagnose_planning_payload` or current diagnose route logic

Acceptance:

- Advanced demo plan endpoint returns scheduled blocks.
- Advanced demo check endpoint returns feasibility estimates.
- Advanced demo diagnose endpoint returns diagnostics.
- Broken references fail before solver.

### Phase B5: fixed example equivalence test

Files:

- `backend/tests/test_universal_planning_adapter.py`

Tasks:

1. Build a Universal record set equivalent to the legacy default frontend dataset.
2. Compile it to `PlanningInput`.
3. Assert key counts and fields match:
   - resources
   - equipment
   - workers
   - products
   - orders
   - inventory
   - policy values
4. Run the existing planner and assert it returns at least one block.

Acceptance:

- The old hard-coded production example is proven configurable through Universal APS.

## Cross-industry template corrections

### Batch process

Add common pages:

- Materials/Inventory
- Demand/Shipments
- Planning Policies

Add rich concepts:

- ingredient
- material_inventory
- cleaning_changeover
- tank_calendar
- campaign_rule
- quality_hold

Critical widgets:

- tank capacity and compatible recipes
- recipe stages
- material consumption
- quality hold duration
- cleaning/setup matrix

### Fulfillment center

Add common pages:

- SKU Inventory
- Orders/Shipments
- Wave Planning Policies

Add rich concepts:

- order
- order_line
- sku_inventory
- dock
- carrier
- cutoff_calendar
- labor_shift

Critical widgets:

- picker-zone skill matrix
- wave line editor
- dock capacity calendar
- SKU inventory and receipts

### Job shop

Add common pages:

- Jobs/Orders
- Material/WIP
- Dispatch Policies

Add rich concepts:

- routing
- operation_precedence
- fixture/tool_pool
- machine_calendar
- material_requirement
- wip_status

Critical widgets:

- job operation sequence editor
- alternate machine selector
- setup/changeover matrix
- machine and operator availability

## Testing plan

### Backend tests

Add or extend tests for:

1. Template validation for all templates.
2. Reference validation success/failure.
3. Required field validation.
4. Enum validation.
5. Data generation deterministic counts.
6. Advanced manufacturing generated data compiles to `PlanningInput`.
7. Advanced manufacturing generated data plans successfully.
8. Fixed example equivalence.

Commands:

```bash
cd backend && uv run python -m unittest tests.test_universal_config tests.test_universal_planning_adapter tests.test_replan_progress
cd backend && uvx ruff check .
```

### Frontend checks

Add Playwright coverage for:

1. APS Studio shows advanced template.
2. Applying advanced template shows rich navigation.
3. Reference fields render as selects.
4. Equipment page includes capability matrix.
5. Worker page includes skills/calendar/overtime.
6. Product page includes workflow/BOM editor.
7. Inventory page includes stock/reservation/receipt sections.
8. Order page includes product/recipe line selectors.
9. Run Plan uses Universal records and returns a schedule.

Commands:

```bash
cd frontend && npm run build
cd frontend && npx playwright test tests/universal-aps.spec.js --config=playwright.config.js
```

## UI quality checklist

Before considering implementation complete:

- Do not expose raw JSON as the main operational interface.
- Do not show Record ID as a primary business column unless needed for debugging.
- Do not render references as plain textboxes.
- Do not hide Orders/Demand and Inventory/Supply for real templates.
- Do not regress legacy fixed APS mode.
- Use table columns chosen by page blueprint, not every field blindly.
- Use compact sections with clear labels and helper text.
- Keep keyboard focus visible.
- Use select/combobox controls for linked data.
- Show validation errors near the offending field or section.
- Keep Plan, Check, and Diagnose tied to the same applied data source.

## Execution order

Implement in this exact order:

1. Backend schema definitions and template validation.
2. Advanced manufacturing template shape.
3. Deterministic advanced manufacturing sample records.
4. Backend record validation, especially references.
5. Backend Universal-to-`PlanningInput` adapter.
6. Universal plan/check/diagnose endpoints.
7. Frontend reference/enum renderers.
8. Frontend page-blueprint navigation.
9. Frontend rich page templates.
10. Frontend Universal Plan binding.
11. Cross-industry template enrichment.
12. Full backend, frontend build, and Playwright validation.

This order prevents UI polish from outrunning the data model and prevents the model from being accepted before it can actually plan.

## Non-goals for the next slice

Do not implement these yet:

- A fully general solver IR for all arbitrary user formulas.
- Arbitrary JavaScript/Python execution from formulas.
- Visual drag-and-drop ontology editor.
- Multi-user authorization.
- Data migration across drastic schema changes.
- Full component extraction or rewrite of `frontend/src/App.vue`.

These can come later after the advanced manufacturing proof works end to end.

## Definition of done

The next implementation is done only when:

1. `Discrete Manufacturing Advanced Demo` can be created/generated from APS Studio.
2. Applying it changes the app to rich APS pages, not generic CRUD.
3. Linked fields use dropdowns/comboboxes sourced from actual records.
4. Orders/Demand and Inventory/Supply remain present in the applied app.
5. The advanced demo compiles to the existing `PlanningInput`.
6. Running Plan from the applied config produces a valid schedule.
7. Backend tests, Ruff, frontend build, and Playwright checks pass.
8. The legacy fixed APS mode still works when no Universal config is applied.
