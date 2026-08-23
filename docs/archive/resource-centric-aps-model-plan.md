# Resource-Centric Universal APS Model and Implementation Plan

> Historical transitional design document (merged into current item-function model direction).
> Current canonical references: `docs/item-function-aps-decision-register.md` and `docs/discrete-factory-rule-catalog.md`.

## Purpose

The current Universal APS design is still too entity/page-oriented. It can render resources, operations, policies, orders, and inventory as separate concepts, but that leaks implementation vocabulary into the business model. In a truly configurable APS, the setup should define a small set of production-factor abstractions that can express manufacturing, buying, outsourcing, maintenance, services, logistics, utilities, workforce, and inventory without hard-coding industry-specific entities.

This document defines the next target model and an implementation plan. It deliberately treats **Order**, **Inventory**, and **Plan** as universal app surfaces, while setup-specific tabs above them are primarily **business resource classes**.

## Research anchors

The model below is based on these primary or standards-adjacent anchors:

- RFC 5545 defines iCalendar as a format for representing and exchanging calendaring and scheduling information, including events, to-dos, free/busy information, recurrence rules, due dates, durations, and resources. This supports using iCalendar-style recurrence/availability as a schedule language rather than custom weekly-only windows. Source: https://datatracker.ietf.org/doc/html/rfc5545
- OASIS WS-Calendar states that agreement on when something should or did occur is fundamental to negotiated services, that long-running physical processes require lead times, and that common schedule communication must support periodic occurrences, local time zones, service coordination, and energy/grid price signals. This supports modeling production and procurement as scheduled service commitments. Source: https://docs.oasis-open.org/ws-calendar/ws-calendar-spec/v1.0/cs01/ws-calendar-spec-v1.0-cs01.html
- W3C OWL-Time models temporal entities as instants or intervals with beginning, end, duration, temporal reference systems, and interval relations such as before/after/overlaps/during. This supports an interval-first internal representation for tasks, availability, holds, leases, degradation, and commitments. Source: https://www.w3.org/TR/owl-time/
- PDDL domain modeling separates stable domain structure from problem instances through object types, predicates, actions, preconditions, and effects. Even though APS uses optimization rather than symbolic planning as the final solver, this validates the setup distinction between **resource classes**, **state predicates/properties**, and **transformation actions**. Source: https://planning.wiki/ref/pddl/domain
- Timefold/OptaPlanner documentation emphasizes domain modeling, planning variables, constraints, and score calculation/constraint-match metrics as first-class concepts in optimization systems. This supports keeping business facts separate from solver decisions and exposing explainable hard/soft score contributions. Source: https://docs.timefold.ai/timefold-solver/latest/constraints-and-score/overview

Additional research notes are being collected in `docs/resource-centric-aps-research.md`.

### Research follow-up incorporated into the plan

The implementation should align with common APS/MOM modeling primitives rather than inventing a private vocabulary:

- ISA-95 / IEC 62264 concepts, publicly reflected through MESA B2MML, separate operation requests from personnel, equipment, physical-asset, and material requirements. That reinforces the decision to keep **activities/transformations** out of the business-resource sidebar while still letting each transformation require many resource kinds.
- Microsoft Dynamics production-control documentation separates BOM/formula structure from routes/operations/resources, including process-manufacturing formulas with co-products/by-products and BOM/formula versions constrained by date, quantity, site, and product dimensions. The resource model therefore needs both discrete BOM and process formula semantics.
- OR-Tools examples show the solver-lowering target: tasks become integer interval variables; machine-like renewable resources use no-overlap; pooled capacity can use cumulative constraints; pickup/delivery and optional-node penalties map to logistics, optional demand, and outsourced alternatives.
- Timefold/OptaPlanner-style domain modeling separates problem facts, planning entities, planning variables, scores, hard/soft constraints, and constraint-match diagnostics. The Universal APS compiler should preserve this separation so users can understand why a plan is infeasible or expensive.
- Calendar handling must be explicit and audited. RFC 5545 RRULE/EXDATE/RDATE is the better canonical model for user-authored calendars; cron can be accepted as convenience syntax, but DST and invalid local-time behavior must not be hidden.

Design implications:

1. Store a canonical planning graph independent of the current CP-SAT adapter: resources, resource instances, activities, requirements, material flows, calendars, constraints, and objective terms.
2. Normalize calendars into finite solver intervals, but preserve the original recurrence expressions for editing and audit.
3. Represent unassigned or dropped work explicitly with penalties when allowed, instead of using fake/dummy resources.
4. Keep industry-specific UI labels friendly, but compile them into common typed primitives.

## Core critique of the current model

### What is wrong

The current `discrete_manufacturing_advanced` template still contains concepts such as:

- `equipment`
- `worker`
- `product`
- `operation`
- `planning_policy`

Some of these are valid business resource classes, but others are not. In particular:

- **Operation** is not a business resource. It is a scheduled transformation/commitment that consumes, occupies, modifies, creates, degrades, or repairs resources.
- **Policy** is not a resource. It is a solver/decision strategy and objective configuration.
- **Order** is not a resource class. It is a demand contract: deliver a bundle of resources before due dates, with rewards/penalties and service constraints.
- **Inventory** is not a resource class. It is the current or future state/quantity/location of resources.

### Correct framing

The setup should define:

1. Resource classes and their properties.
2. Resource states and inventory ledgers.
3. Transformation recipes/actions that change resource states over intervals.
4. Demand contracts requesting resources by time.
5. Calendars/costs/formulas/constraints that affect feasible transformations.
6. Solver goals/policies as abstract plan configuration, not sidebar resources.

The app shell should always show:

```text
Business resource classes
---
Order
Inventory
Plan
```

APS Studio should be the configuration gear, not a peer planning surface.

## Universal resource model

### 1. Resource class

A `ResourceClass` describes a type of thing the plan can use, produce, buy, sell, reserve, maintain, or track.

Examples:

- Finished good
- Raw material
- Component
- Machine
- Worker
- Tool
- Fixture
- Tank
- Warehouse zone
- Truck
- Operating room
- Nurse
- Surgeon
- Electricity
- Water
- Gas
- Cloud VM
- Supplier capacity
- Outsourced service
- Maintenance crew

Fields:

```json
{
  "id": "machine",
  "label": "Machine",
  "kind": "asset",
  "stock_unit": "each",
  "capacity_unit": "machine-hour",
  "countability": "discrete",
  "can_be_stored": false,
  "can_be_occupied": true,
  "can_be_consumed": false,
  "can_be_produced": false,
  "can_be_purchased": false,
  "can_be_maintained": true,
  "properties": [],
  "state_schema": [],
  "availability": {},
  "cost_model": {},
  "ui": {}
}
```

Key design point: a person, machine, component, raw material, gas, electricity, supplier capacity, room, and software server are all resources. Their behavior differs through capabilities and effect semantics, not through hard-coded entity types.

### 2. Resource instance

A `ResourceInstance` is a named item, pool, or lot belonging to a class.

Examples:

- `CNC-1` as one machine instance.
- `Alice` as one worker.
- `STEEL-A36` as a material pool.
- `ELEC` as electricity supply.
- `AWS-GPU-P4D` as external compute capacity.
- `SUPPLIER-X-CAPACITY` as outsourceable service capacity.

Fields:

```json
{
  "id": "cnc-1",
  "class_id": "machine",
  "label": "CNC 1",
  "quantity": 1,
  "location": "plant-a",
  "properties": {
    "precision_mm": 0.01,
    "spindle_power_kw": 12
  },
  "state": {
    "condition": 0.92,
    "status": "available"
  }
}
```

Instances are optional for fungible resources. For example, material inventory can be tracked as lots or as pooled quantities.

### 3. Resource state / inventory ledger

Inventory is a state ledger over resource classes/instances.

It must support:

- on-hand quantity
- safety stock
- future receipts
- reservations
- allocations
- WIP
- location
- lot/batch/serial
- expiry/shelf-life
- quality status
- condition/degradation
- ownership/consignment

Generic ledger event:

```json
{
  "resource_class_id": "steel",
  "resource_instance_id": "lot-2026-07-a",
  "event_type": "receipt",
  "quantity": 1200,
  "unit": "kg",
  "effective_time": "2026-07-17T08:00:00+08:00",
  "properties": {
    "quality_status": "released"
  }
}
```

### 4. Demand contract / order

An order is a demand contract, not a resource class. It requests one or more resource outcomes.

```json
{
  "id": "order-1001",
  "requested_resources": [
    {
      "resource_class_id": "finished-widget",
      "quantity": 50,
      "unit": "each",
      "required_properties": {
        "grade": "A"
      }
    }
  ],
  "release_time": "2026-07-16T08:00:00+08:00",
  "due_time": "2026-07-20T17:00:00+08:00",
  "early_reward_formula": "hours_early * 2",
  "late_penalty_formula": "hours_late * priority_weight * 50",
  "service_class": "priority",
  "allow_partial": true
}
```

### 5. Transformation action

A `TransformationAction` is the central abstraction replacing operation/routing hard-coding.

It describes an interval activity that has:

- produced resources
- consumed resources
- occupied resources
- degraded resources
- repaired resources
- transformed resource properties/states
- emitted costs/rewards/risks

```json
{
  "id": "make-widget",
  "label": "Make Widget",
  "produces": [
    {"resource_class_id": "finished-widget", "quantity_formula": "batch_qty"}
  ],
  "requires": [
    {"resource_class_id": "cnc-machine", "mode": "occupy", "quantity": 1},
    {"resource_class_id": "operator", "mode": "occupy", "quantity": 1},
    {"resource_class_id": "steel", "mode": "consume", "quantity_formula": "batch_qty * 2.4"},
    {"resource_class_id": "electricity", "mode": "consume_rate", "rate_formula": "machine.kw * load_factor"}
  ],
  "effects": [
    {"resource_class_id": "cnc-machine", "mode": "degrade", "quantity_formula": "duration_hours * 0.002"}
  ],
  "duration_formula": "setup_hours + batch_qty * run_hours_per_unit / efficiency",
  "eligibility_formula": "machine.precision_mm <= product.required_precision_mm and operator.skill >= 0.8",
  "calendar_id": "plant-production-calendar",
  "cost_formula": "machine_hour_cost + labor_cost + electricity_cost"
}
```

### 6. Transformation graph / BOM

BOM and routing become a dependency graph of transformations that can satisfy requested resources.

Relationships:

- `produces`: action creates a resource.
- `consumes`: action uses up resource stock.
- `occupies`: action reserves finite capacity for an interval but returns it.
- `degrades`: action reduces condition/life/quality.
- `repairs`: action increases condition/life/status.
- `substitutes`: resource A can satisfy resource B with conversion rules.
- `outsources`: supplier action can produce/buy requested resource with lead time/cost.
- `buys`: procurement action produces inventory receipt after lead time.
- `transports`: action changes location of resource.
- `holds`: action or constraint blocks resource until condition/time/event.

The old BOM tree is a special case:

```text
Order demands finished resource
  -> make action produces finished resource
     -> consumes component resources
        -> make/buy actions produce component resources
```

### 7. Calendar / recurrence

Every resource class, instance, transformation action, supplier, and demand contract may have schedules:

- availability
- blackout
- maintenance
- price bands
- capacity bands
- delivery calendars
- labor shifts
- service windows

Use this representation:

```json
{
  "calendar_id": "plant-day-shift",
  "timezone": "Asia/Shanghai",
  "rules": [
    {"kind": "include", "rrule": "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR", "start_time": "08:00", "end_time": "17:00"},
    {"kind": "exclude", "date": "2026-10-01"}
  ]
}
```

The first implementation can store RRULE strings and expand only a safe subset. Cron expressions can be accepted as a convenience syntax, but RRULE is a better canonical model because it is designed for calendars, date-times, recurrence, exceptions, and free/busy semantics.

### 8. Effect semantics

Resource usage must distinguish:

| Mode | Meaning | Example |
| --- | --- | --- |
| `consume` | Quantity is used up at start or during interval | steel, chemicals |
| `consume_rate` | Quantity consumed per time | electricity, gas, water |
| `occupy` | Capacity unavailable during interval but returned after | machine, worker, room |
| `produce` | Quantity becomes available after interval | finished goods, repaired machine |
| `transform` | State/properties changed | raw -> cured, dirty -> clean |
| `degrade` | Condition/life decreases | tool wear, battery cycle |
| `repair` | Condition/status improves | maintenance |
| `reserve` | Quantity/capacity earmarked | allocated inventory |
| `transport` | Location changes | truck move |
| `hold` | Resource unavailable until release | QA hold, quarantine |

### 9. Policy and objective model

Policies are not resources. They belong in a pinned abstract planning configuration:

```json
{
  "objective_profile": "balanced",
  "hard_constraints": ["no_negative_inventory", "finite_capacity", "calendar"],
  "soft_objectives": [
    {"id": "lateness", "formula": "sum(order.hours_late * order.penalty_rate)"},
    {"id": "cost", "formula": "sum(action.cost)"},
    {"id": "stability", "formula": "sum(abs(new_start - prior_start) * move_penalty)"}
  ],
  "solver_budget": {
    "max_seconds": 10,
    "max_alternatives_per_action": 20
  }
}
```

### 10. Formula model

Formula use cases:

- duration
- cost
- eligibility
- yield
- resource consumption
- degradation
- reward/penalty
- substitution conversion
- priority

Rules:

- Formulas are declarative expressions, not code.
- No Python/JS execution.
- Typed variables only.
- Units must be declared.
- Unsupported nonlinear expressions must be rejected or evaluated as precomputed coefficients.
- First implementation supports deterministic arithmetic/comparison/boolean formulas and safe functions: `min`, `max`, `abs`, `round`, `if`.

## Cross-industry challenge scenarios

### Discrete manufacturing

Resources:

- finished product
- components
- machines
- workers
- tooling
- electricity

Actions:

- make component
- assemble product
- inspect
- rework
- buy component
- maintain machine

The old fixed setup maps cleanly.

### Batch/process manufacturing

Resources:

- tank/reactor
- ingredient
- batch lot
- quality lab
- steam/water/electricity

Actions:

- mix
- heat
- hold
- clean tank
- release QA
- package

Needs sequence-dependent cleaning and lot/quality state. Supported by transform/hold/consume_rate/occupy.

### Fulfillment/logistics

Resources:

- SKU
- picker
- zone
- dock
- carrier capacity
- truck

Actions:

- pick
- pack
- wave
- load
- ship

Orders request SKU quantities by promised datetime. Inventory supplies SKU. Workers/zones/docks are occupy resources.

### Field service / workforce

Resources:

- technician
- vehicle
- spare part
- service slot
- customer asset

Actions:

- travel
- repair
- inspect

Location and travel time become formulas/constraints. First implementation can defer route optimization but keep model hooks.

### Maintenance/repair

Resources:

- asset condition
- spare parts
- technician
- downtime window

Actions:

- inspect
- repair
- replace
- calibrate

Maintenance is not special: it is a transformation that consumes parts/labor and repairs/degrades/changes an asset state.

### Energy/utilities

Resources:

- power capacity
- gas
- water
- battery state of charge
- price signal

Actions:

- consume power
- charge
- discharge
- produce heat/cooling

Needs time-varying price/capacity calendars. Supported by schedule bands and formulas.

### Healthcare/OR scheduling

Resources:

- OR room
- surgeon
- nurse
- equipment kit
- bed
- patient demand

Actions:

- procedure
- turnover/cleaning
- recovery

Patient/order is demand contract. Rooms/staff/equipment are occupy resources. Sterile kits/inventory are consume/occupy depending on use.

## What to defer

Defer these until after the first resource-centric slice:

- Full route/travel optimization.
- Stochastic yields/probabilistic duration.
- Multi-echelon network planning.
- Arbitrary nonlinear optimization.
- Full temporal logic or PDDL planner.
- Full RRULE implementation beyond weekly/daily/date exclusions.
- Multi-tenant auth and approvals.

## Target backend shape

Add a new versioned setup model parallel to current templates:

```text
ResourceSetup
  resource_classes[]
  calendars[]
  transformations[]
  demand_schema
  inventory_schema
  policies
  formulas
  ui_schema
```

For compatibility, store it inside Universal config payload:

```json
{
  "template_key": "resource_model_discrete_manufacturing",
  "schema_version": 2,
  "model_kind": "resource_model_v1",
  "resources": [],
  "calendars": [],
  "transformations": [],
  "demand": {},
  "inventory": {},
  "policies": {},
  "ui_schema": {}
}
```

Do not delete existing concept templates. Keep them working while adding the new model.

## Target frontend shape

Sidebar:

```text
APS        [gear]

Business resources
  Finished Good
  Component
  Machine
  Worker
  Utility
  Supplier Capacity

Order
Inventory
Plan
Run Plan
Diagnose
```

APS Studio setup pages:

1. Resource classes
2. Transformations
3. Calendars
4. Formulas
5. Policy/objective
6. Sample data
7. Compile diagnostics

Applied app pages:

- Business resource class pages above the pinned bottom.
- Order page always present.
- Inventory page always present.
- Plan page always present.

## Implementation plan

### Phase 1: documentation and research

1. Save this plan.
2. Save primary-source research in `docs/resource-centric-aps-research.md`.
3. Record examples for at least:
   - discrete manufacturing
   - batch process
   - fulfillment
   - field service
   - maintenance
   - healthcare/OR
   - energy/utilities

Acceptance:

- Docs explain why operations/policies are not resources.
- Docs define transformation/effect semantics.
- Docs define how old fixed manufacturing maps without hard-coded equipment/worker/product concepts.

### Phase 2: resource-model template without solver replacement

Files:

- `backend/aps/universal/models.py`
- `backend/tests/test_universal_config.py`

Tasks:

1. Add `resource_model_discrete_manufacturing` template.
2. Add `model_kind: "resource_model_v1"`.
3. Define `resources[]` for:
   - finished good
   - component/raw material
   - machine
   - worker
   - utility
   - tool
   - supplier capacity
4. Define `transformations[]` for:
   - buy material
   - cut
   - assemble
   - inspect
   - rework
   - maintain machine
5. Define calendars using RRULE-like fields.
6. Define policies as top-level abstract plan settings, not sidebar concepts.
7. Generate sample records from this setup.

Acceptance:

- Template appears in APS Studio.
- Applying it shows business resource classes above Order/Inventory/Plan.
- No Operations or Policies appear in the business resource list.

### Phase 3: resource-model compiler to existing `PlanningInput`

Files:

- `backend/aps/universal/api.py`
- new `backend/aps/universal/resource_model.py` if needed
- `backend/tests/test_universal_resource_model.py`

Tasks:

1. Compile resource model classes/actions into existing `PlanningInput`.
2. Map resource classes with `role: capacity_asset` to equipment/tool/worker where possible.
3. Map resource classes with `role: material` or `role: finished_good` to products/inventory.
4. Map transformations to workflows/recipes.
5. Map consume/occupy/produce/degrade effects to the closest supported fixed planner fields.
6. Reject unsupported effects with clear diagnostics.

Acceptance:

- Resource-model discrete manufacturing sample plans successfully.
- It can express the old fixed example without hard-coded manufacturing-specific concept names in the setup runtime.

### Phase 4: frontend applied resource-model runtime

Files:

- `frontend/src/App.vue`
- `frontend/tests/universal-aps.spec.js`

Tasks:

1. Detect `model_kind === "resource_model_v1"`.
2. Build top nav from `payload.resources[]`, not `payload.concepts[]`.
3. Keep Order/Inventory/Plan pinned at bottom.
4. Add Studio summaries for:
   - resource classes
   - transformations
   - calendars
   - policies
5. Render resource-class pages with properties, availability, cost model, and sample instances.

Acceptance:

- Business resources are visually separated from policies/actions.
- Order and Inventory remain foundational.
- Plan uses the resource-model endpoint where available.

### Phase 5: formula and calendar hardening

Tasks:

1. Implement formula parser/validator for safe arithmetic/comparison/boolean expressions.
2. Add unit metadata to formula variables.
3. Add RRULE subset parser/validator:
   - daily
   - weekly
   - BYDAY
   - date exclusions
   - timezone
4. Expand recurring availability into planning windows.

Acceptance:

- Invalid formulas fail validation before planning.
- Invalid calendar rules fail validation before planning.
- Weekly legacy availability can be expressed as RRULE.

## First implementation slice after this doc

Implement only:

1. `resource_model_discrete_manufacturing` template.
2. Deterministic sample data.
3. Frontend navigation/runtime recognition for `resource_model_v1`.
4. Tests proving:
   - no Operations or Policies in business resources,
   - Order/Inventory/Plan pinned,
   - template can be created and applied.

Do not replace the solver yet in this slice. Add the compiler in the next slice after the resource model is visible and stable.

## Definition of done for the first slice

- Existing Universal APS tests still pass.
- New resource-model template appears in APS Studio.
- Applying it shows resource classes only in the top business-resource group.
- Order, Inventory, and Plan remain pinned below.
- Operations/transformations and policy are visible in APS Studio/config detail, but not as resource pages.
- Documentation exists for the model and implementation sequence.
