# Item-Function Universal APS Architecture

> Reference-only structural document (frozen semantics).
> Authoritative kernel semantics: `docs/item-function-aps-decision-register.md`
> Industrial examples and hard-case evidence: `docs/discrete-factory-rule-catalog.md`
> Index: `docs/design-doc-index.md`

> **Current authority note:** This document still contains earlier Item/Resource/Capability/Tag/Path terminology. The current kernel direction is flat item state plus equipment function selectors and finite deterministic transformation rules. Where this document conflicts with the decision register or rule catalog, those newer documents take precedence until this architecture is fully rewritten.

## Purpose

This document captures the agreed target design for a configurable APS kernel where business-specific behavior is modeled as data instead of code. The core idea is:

> APS is an item-flow and capacity-allocation engine. Items move through inventory and production paths. Resources provide capabilities over time. Steps consume/produce items, occupy resources, change resource state, and move things between locations. Tags describe domain-specific attributes without changing the core model.

The design priorities are, in order:

1. **Correctness**: plans must respect item conservation, capacity, time, expiry, state, and locked execution.
2. **High performance**: configuration must compile into a finite, pruned planning graph suitable for CP-SAT and future solver adapters.
3. **Function richness**: manufacturing, procurement, outsourcing, movement, waste, rework, utilities, maintenance, and setup/changeover must fit the same model.
4. **Clear structure**: backend modules should be deep, with small interfaces hiding compiler, validation, and solver complexity.
5. **Extensibility**: new industries and concepts should usually require data changes, not code changes.
6. **Minimality**: avoid duplicate concepts, duplicate jobs, special-case fields, and shallow pass-through modules.

## Design conclusion

The new target architecture is:

```text
Item-flow + Resource-capability + Tag-selector + State-graph APS kernel
```

The stable meta-kernel is small. Business users configure:

- Items
- Tags
- Locations
- Resources
- Capabilities
- Production paths and steps
- Resource state graphs
- Orders
- Inventory lots
- objective/accounting items such as MONEY, WASTE, CO2, or RISK

The kernel understands only a small number of physical semantics:

- an item quantity exists in inventory at a location with tags and expiry;
- a step removes matching item quantities from inventory while running;
- a step occupies resources providing required capabilities;
- a step may require and/or change resource state;
- a step emits item quantities back to inventory;
- a step may move items/resources by producing them at another location or changing resource location;
- orders demand item quantities by deadlines;
- plans may be locked or realized.

Everything else is configured data.

## Non-goals

- Do not build an MES. The APS can import/realize execution state, but real execution tracking belongs to MES/shop-floor systems.
- Do not implement arbitrary programming in formulas. Formulas must be sandboxed, typed, deterministic expressions.
- Do not support every rare parallel-resource edge case in the first kernel. Use logical resource splitting for rare multi-lane resources.
- Do not make all fields tags. Keep APS-physics-critical fields as real attributes; use tags for domain-specific semantics.
- Do not claim ISA-95, B2MML, or ERP conformance until integration contracts are explicitly implemented.

## Core concepts

### Item

An `Item` is anything that can exist as a quantity in inventory or be consumed/produced by a step.

Examples:

- raw material
- component
- WIP if explicitly bufferable
- finished good
- packaging
- electricity
- gas
- water
- scrap
- failed-QA product
- money
- emissions allowance
- disposal capacity token

In the rule-driven model, every compiled item is a flat object with these reserved fields:

```json
{
  "type": "steel_a36_kg",
  "value": 500,
  "price": 650,
  "material": "steel"
}
```

Rules:

- Units are encoded in item identity; the engine has no separate unit field.
- `value` is the integer virtual value of one item quantum to the company.
- `price` is the integer virtual external acquisition/replacement cost of one item quantum.
- Items that are not normally sold still carry a high virtual `price`.
- `price` does not automatically create a procurement path; a purchase rule must still define lead time, equipment, batch limits, and output location.
- Other keys are flat selector properties. Some keys such as `type`, `value`, `price`, and `location` are compiler-known; other keys are opaque equality-match data.
- If an intermediate can wait for a long time, model it as a real item. If it is inline/no-wait/bounded-wait, keep it inside a production path.

### Objective/accounting item

Money can be modeled as an item, but it has special objective semantics.

```json
{
  "id": "MONEY",
  "unit": "cent",
  "infinite_inventory": true,
  "manufacturable": false,
  "objective_weight": 1
}
```

This lets buying, outsourcing, licensing, piecework labor, utilities, disposal, overtime, and other economic costs use ordinary item consumption:

```text
Buy steel: MONEY -> STEEL
Outsource assembly: MONEY + COMPONENT -> ASSEMBLY
Dispose scrap: SCRAP + MONEY -> nothing
Generate electricity: MONEY -> ELECTRICITY
```

The same mechanism can represent non-money objectives:

- `CO2`
- `RISK_POINT`
- `WASTE_KG`
- `OVERTIME_POINT`

The objective minimizes weighted consumption of objective items plus lateness, instability, or other configured penalties.

### Inventory lot

Inventory is the realized or planned existence of items.

```json
{
  "item": {
    "type": "steel_a36_kg",
    "location": "plant_a_raw_storage",
    "value": 500,
    "price": 650
  },
  "quantity": 1200,
  "expires_at": "2026-08-01T00:00:00+08:00"
}
```

Stacking rule:

> Inventory lots may stack only when their complete item objects and expiry are exactly equal.

Inventory should stay minimal and physical:

- what
- where
- count
- expiry
- flat properties

Checks, QA inspection, quarantine, and rework should usually be modeled as steps. If a business must store held/released stock visibly, represent that as tags such as `quality=held` or `quality=released`.

### Tag

Tags provide domain-specific classification without adding columns or changing the meta-model.

```json
{
  "id": "allergen_milk",
  "parents": ["allergen"],
  "value_type": "boolean",
  "exclusive_group": null
}
```

Valued tag example:

```json
{
  "id": "quality",
  "value_type": "enum",
  "allowed_values": ["unchecked", "released", "failed", "scrap"],
  "exclusive_group": "quality"
}
```

Tag rules:

- Tags may inherit from parent tags.
- Tag expansion is computed during compilation.
- Exclusive groups prevent contradictory tags such as `quality=released` and `quality=failed`.
- Tags are used by item selectors, resource eligibility, affinity, setup/state transitions, quality diversion, and UI filtering.
- Tags are not a replacement for kernel fields such as item id, quantity, location, expiry, deadline, or resource state.

### Location

Location is important enough to be a kernel concept.

```json
{
  "id": "LINE-1",
  "label": "Line 1",
  "parent_location_id": "PLANT-A",
  "tags": ["production_area"]
}
```

Locations support:

- inventory distinction;
- movement steps;
- resource travel/setup time;
- warehouse/line/dock constraints;
- hierarchical grouping.

The first implementation may use location ids and formula-based travel time. A later version can add coordinates and routing.

### Capability

A `Capability` is a typed unit of work that a resource can provide and a step can demand.

```json
{
  "id": "milling",
  "label": "Milling",
  "unit": "mm_cut"
}
```

Use one canonical unit per capability. Avoid unit conversion in the first version.

### Resource

A `Resource` is a non-consumable capacity provider.

Examples:

- machine
- worker
- fixture
- tool head
- forklift
- oven
- truck
- clean room

```json
{
  "id": "CNC-1",
  "label": "CNC 1",
  "location_id": "LINE-1",
  "calendar_id": "weekday_shift",
  "current_state": "off",
  "tags": {"machine_class": "advanced_cnc"},
  "provided_capabilities": [
    {
      "capability_id": "milling",
      "rate_per_second": 20,
      "batch_capacity": 1,
      "cost_items_per_second": [{"item_id": "ELECTRICITY", "quantity": 0.4}],
      "affinity_rules": []
    }
  ]
}
```

Resource simplification:

> One resource provides exactly one capability to one active step at a time. Batch capacity covers multiple units in one pass. If a real machine can independently run multiple jobs, model it as multiple logical resources. If a function requires both sides of a dual machine, require both logical resources.

This keeps capacity constraints simple and performant.

### Batch capacity

Use `batch_capacity`, not `parallelism`, for “N units in one pass.”

Examples:

- oven bakes up to 100 parts in 2 hours;
- washer cleans up to 10 trays in one cycle;
- furnace treats 500 kg per run.

Batch capacity is not simultaneous independent scheduling. It is a step quantity rule.

### Affinity

Affinity modifies effective capability rate or duration based on local, tag-driven conditions.

Affinity should live near the object it modifies:

- resource-provided capability;
- tool;
- worker skill;
- production path;
- item;
- state.

Example:

```json
{
  "label": "Advanced CNC with expert worker on titanium",
  "applies_when": {
    "item_tags": {"material": "titanium"},
    "co_assigned_resource_tags": {"worker_skill": "expert"},
    "resource_tags": {"machine_class": "advanced_cnc"}
  },
  "target_capability_id": "milling",
  "multiplier": 1.5,
  "affinity_group": "tooling_speed"
}
```

Combination rules:

- same affinity group defaults to `max`;
- different groups may multiply;
- configs can set `max`, `multiply`, `add`, or `override`;
- compiler diagnostics must report all applied affinity rules.

This prevents accidental unbounded multiplier stacking.

### Resource state graph

Resource setup/changeover/cleaning/warmup/maintenance is modeled as a directed graph.

```json
{
  "resource_id": "STOVE-1",
  "states": ["off", "cold", "cold:A", "cold:B", "warm", "hot", "hot:C"],
  "edges": [
    {
      "from": "hot:C",
      "to": "hot",
      "label": "cleanup C",
      "duration_seconds": 600,
      "consumes_items": [{"item_id": "CLEANING_AGENT", "quantity": 1}]
    },
    {
      "from": "hot",
      "to": "warm",
      "duration_seconds": 900
    },
    {
      "from": "warm",
      "to": "cold",
      "duration_seconds": 1200
    },
    {
      "from": "cold",
      "to": "cold:A",
      "duration_seconds": 300
    }
  ]
}
```

Graph, not tree, is the core representation. A tree UI can be provided for convenience, but the compiler lowers it to a graph.

State transition planning:

1. Precompute candidate transition paths between states.
2. Keep a small Pareto frontier, not just one shortest path, because time/cost tradeoffs matter.
3. Feed only the top K candidates into the APS solver.
4. Solver chooses between production activities and precomputed state-transition candidates.

This gives correctness without exploding the global optimization problem.

### Item selector

Steps and orders need selectors, not just item ids.

```json
{
  "item_id": "STEEL_A36",
  "quantity": 100,
  "location_id": "WH-A",
  "required_tags": {"quality": "released"},
  "forbidden_tags": ["expired"],
  "expiry_after": "2026-07-20T00:00:00+08:00"
}
```

Selectors support:

- exact item matching;
- location;
- tag inheritance;
- required/forbidden tags;
- expiry windows;
- quality diversion;
- substitute groups in a later version.

### Step

A `Step` is the schedulable unit inside a production path. It is the only thing that changes the world over time.

```yaml
id: inspect_component
equipments:
  - function: inspect_component
batch:
  minimum: 1
  maximum: 50
consume:
  - item: { type: component_awaiting_inspection_each }
    quantity: 100
produce:
  - item: { type: component_each }
    quantity: 98
  - item: { type: rejected_component_each }
    quantity: 2
duration: 30m
```

Step rules:

- Inputs are unavailable while the step runs.
- Occupied resources are unavailable while the step runs.
- Outputs appear only when the step completes or is realized.
- If a step fails during real execution, non-consumed occupied inputs may return to inventory through MES/import logic. APS planning uses deterministic planned outputs.
- APS rules never contain uncertain outcomes. Statistical yield is represented as deterministic fixed output ratios, producing accepted, rejected, scrap, and other outcome items simultaneously. Actual execution variance is imported later and triggers replanning.
- The engine accepts integers only. The selected batch quantity is an integer multiplier of the complete consume/produce vector.

### Production path

A `ProductionPath` is an alternative way to produce one or more item outputs.

```json
{
  "id": "make_component_a",
  "output_items": [{"item_id": "COMPONENT_A"}],
  "steps": ["cut_blank", "mill_component", "inspect_component"],
  "batch_rule": {"min_qty": 1, "max_qty": 50, "multiple_of": 1}
}
```

Production paths cover:

- internal manufacturing;
- buying;
- outsourcing;
- movement;
- disposal;
- rework;
- maintenance support flows;
- utilities generated from money;
- co-products/by-products/waste.

Examples:

```text
Buy steel: MONEY -> STEEL
Dispose scrap: SCRAP + MONEY -> nothing
Rework failed QA: FAILED_GOOD + LABOR + MONEY -> RELEASED_GOOD
Move steel: STEEL at WH-A + FORKLIFT -> STEEL at LINE-1
```

### Wait policy

Inline path steps need explicit wait semantics:

```json
{
  "type": "no_wait"
}
```

```json
{
  "type": "bounded_wait",
  "min_seconds": 7200,
  "max_seconds": 21600
}
```

```json
{
  "type": "bufferable"
}
```

Rules:

- `no_wait`: next step starts immediately.
- `bounded_wait`: next step starts within a time window.
- `bufferable`: intermediate should usually be modeled as an actual item/inventory lot.

### Order

An order requests items by deadline.

```json
{
  "id": "ORD-1001",
  "requested_items": [
    {"item_id": "FINISHED_WIDGET", "quantity": 50, "required_tags": {"quality": "released"}}
  ],
  "destination_location_id": "DOCK-1",
  "release_time": "2026-07-17T08:00:00+08:00",
  "deadline": "2026-07-20T17:00:00+08:00",
  "early_reward_items_per_second": [{"item_id": "MONEY", "quantity": 0}],
  "late_penalty_items_per_second": [{"item_id": "MONEY", "quantity": 500}]
}
```

Safety stock can be represented as a low-priority internal order.

### Plan

A plan is a proposed future world-state trajectory:

- selected production/procurement/disposal/movement paths;
- step start/end times;
- resource assignments;
- inserted state transitions;
- inventory ledger;
- objective item consumption;
- lateness/earliness;
- realized/pending/locked markers.

Plans are not execution truth. Execution truth comes from MES/import/auto-realize.

### Execution and MES placeholder

Since a real MES is not in scope, the UI should provide:

```text
Import from MES
```

If no MES integration is configured, show:

```text
MES integration is not configured. For demo mode, auto-realize elapsed plan steps?
```

Auto-realize behavior:

1. Find planned steps with `end <= now`.
2. Apply their planned effects to actual inventory and resource state.
3. Mark steps as realized.
4. Leave future steps as pending.
5. Replan future unlocked steps from now when requested.

Maintain separate ledgers:

- planned ledger;
- actual ledger.

This avoids pretending APS is MES while keeping demos usable.

## Sentinel semantics

`-1` is allowed only for limit-like fields:

| Field family | `-1` meaning |
| --- | --- |
| storage limit | unlimited |
| batch max quantity | unlimited within other constraints |
| availability end bound | unbounded, if explicitly documented |

Do not use `-1` as a cost. Costs and item quantities must be non-negative unless the field is explicitly a reward.

For impossible options, prefer omitting the option. If the UI needs a disabled row, represent it as disabled metadata rather than a negative cost.

## Solver semantics

### Duration from capabilities

For a step requiring one capability:

```text
duration >= required_amount / effective_rate
```

For multiple capabilities:

```text
duration >= max(required_amount_i / effective_rate_i)
```

For batch/cycle processes, duration may be fixed or formula-based:

```text
duration = setup + cycle_time
```

where batch quantity must satisfy the path batch rule.

### Effective rate

```text
effective_rate = base_rate * affinity_multiplier * state_multiplier
```

All applied multipliers must be explainable.

### Item conservation

For non-infinite items:

```text
inventory_start
+ produced
+ receipts
- consumed
- expired
- shipped
- disposed
>= 0
```

at every event boundary.

For storage limits:

```text
inventory_quantity <= storage_limit
```

unless storage limit is `-1`.

### Expiry

Expired lots cannot satisfy selectors requiring usable inventory. Expiry should be evaluated at the time the lot is consumed or shipped.

### Resource capacity

One resource can be assigned to only one active step or state transition at a time.

Logical resource splitting handles rare multi-lane resources:

```text
OVEN-LANE-1
OVEN-LANE-2
FULL-OVEN-HEAT requires both lanes
```

### State transitions

If a step requires a resource state different from the current/planned state, the compiler inserts optional candidate transition activities. The solver chooses a feasible transition candidate before the dependent step.

### Movement

Movement is a step:

- consumes/occupies an item lot at source location;
- requires movement capability;
- produces the item at destination location.

For v1, resource travel can be implicit in duration/cost formula. Later it can become explicit resource movement steps.

## Backend architecture

The backend should be reorganized around deep modules. Callers should not know solver internals, validation internals, tag expansion, state graph search, or inventory ledger mechanics.

### Package layout target

```text
backend/aps/
  universal/
    api.py
    persistence.py
    models.py
    item_function/
      schema.py
      validation.py
      normalization.py
      tags.py
      selectors.py
      calendars.py
      state_graph.py
      formula.py
      compiler.py
      planner.py
      ledger.py
      diagnostics.py
      samples.py
      ports.py
      adapters/
        cpsat.py
        in_memory.py
```

This should be introduced incrementally. Do not rewrite the existing planner in one change.

### External backend interface

The central backend module should expose one deep interface:

```python
class ItemFunctionPlanner:
    def validate_setup(self, setup: ItemFunctionSetup) -> ValidationReport: ...
    def generate_sample_data(self, setup: ItemFunctionSetup, seed: int, mode: str) -> SampleData: ...
    def plan(self, problem: PlanningProblem) -> PlanningResult: ...
    def diagnose(self, problem: PlanningProblem) -> DiagnosticReport: ...
    def auto_realize(self, plan_id: str, now: datetime) -> RealizationResult: ...
```

This is the main seam. The API layer calls this module and does not know:

- how tags are expanded;
- how selectors are matched;
- how state transition candidates are generated;
- how production paths are expanded;
- how CP-SAT variables are created;
- how objective terms are assembled.

### Module responsibilities

#### `schema.py`

Owns Pydantic/domain models for:

- `ItemFunctionSetup`
- `TagDefinition`
- `ItemDefinition`
- `InventoryLot`
- `Location`
- `Capability`
- `Resource`
- `ProvidedCapability`
- `StateGraph`
- `ProductionPath`
- `Step`
- `Order`
- `PlanningProblem`
- `PlanningResult`

Interface:

```python
ItemFunctionSetup.model_validate(payload)
PlanningProblem.model_validate(payload)
```

Invariants:

- no negative quantities except documented sentinel fields;
- units are present;
- ids are stable strings;
- references are syntactically valid, not necessarily resolved.

#### `validation.py`

Deep module for semantic validation.

Interface:

```python
validate_setup(setup: ItemFunctionSetup) -> ValidationReport
validate_problem(problem: PlanningProblem) -> ValidationReport
```

Responsibilities:

- reference integrity;
- tag exclusive group conflicts;
- impossible item selectors;
- missing MONEY/objective item if objective references it;
- cycles in production graph;
- state graph reachability;
- invalid batch rules;
- unsafe formula variables;
- calendar syntax;
- inventory stacking normalization.

Validation returns structured diagnostics, not raw exceptions, except for malformed API input.

#### `normalization.py`

Deep module that canonicalizes user input.

Interface:

```python
normalize_setup(setup: ItemFunctionSetup) -> NormalizedSetup
normalize_problem(problem: PlanningProblem) -> NormalizedProblem
```

Responsibilities:

- default values;
- tag expansion;
- sorted inventory tags;
- stable ids for generated internal nodes;
- `-1` sentinel normalization;
- canonical time units;
- canonical quantity precision.

#### `tags.py`

Owns tag taxonomy and matching.

Interface:

```python
expand_tags(tags: TagSet, taxonomy: TagTaxonomy) -> ExpandedTagSet
matches(selector_tags: TagSelector, candidate_tags: ExpandedTagSet) -> bool
```

This concentrates tag inheritance, valued tags, exclusive groups, and conflict handling.

#### `selectors.py`

Owns item/resource selector matching.

Interface:

```python
match_inventory(selector: ItemSelector, lots: Iterable[InventoryLot], at: datetime) -> list[InventoryMatch]
match_resources(selector: ResourceSelector, resources: Iterable[Resource]) -> list[Resource]
```

Selectors should be testable without a solver.

#### `calendars.py`

Owns recurrence validation and expansion.

Interface:

```python
expand_calendar(calendar: Calendar, horizon: TimeHorizon) -> list[TimeWindow]
```

Rules:

- canonical model is RRULE-like with timezone and exceptions;
- cron may be supported later as input syntax;
- invalid recurrence instances are ignored with diagnostics.

#### `state_graph.py`

Owns resource state transition preprocessing.

Interface:

```python
candidate_transitions(graph: StateGraph, from_state: str, to_state: str, limit: int) -> list[TransitionCandidate]
```

Responsibilities:

- graph validation;
- reachability;
- Pareto frontier over duration/objective-item cost/required capability;
- top-K pruning;
- explainability of chosen path.

#### `formula.py`

Owns safe formula parsing/evaluation.

Interface:

```python
compile_formula(expr: str, scope: FormulaScope) -> CompiledFormula
evaluate_formula(compiled: CompiledFormula, values: Mapping[str, Any]) -> Decimal | bool | str
```

Rules:

- no Python/JS execution;
- deterministic only;
- typed variables;
- allowed functions: `min`, `max`, `abs`, `ceil`, `floor`, `round`, `if`;
- reject unsupported nonlinear solver expressions unless precomputable.

#### `ledger.py`

Owns inventory event simulation and explanation.

Interface:

```python
project_ledger(initial: list[InventoryLot], events: list[LedgerEvent]) -> LedgerProjection
```

Responsibilities:

- item conservation;
- expiry;
- stacking;
- storage limits;
- planned vs actual ledger;
- safety stock pseudo-orders.

This module is solver-independent and should be heavily unit-tested.

#### `compiler.py`

Deep module that converts normalized business setup/problem into a canonical planning graph.

Interface:

```python
compile_problem(problem: NormalizedProblem) -> CompiledPlanningGraph
```

Responsibilities:

- demand expansion;
- production path expansion;
- buy/make/outsource/dispose alternatives;
- movement requirements;
- state transition candidate insertion;
- capability requirement generation;
- item flow graph;
- dominance pruning;
- horizon pruning;
- explainable unsupported-feature diagnostics.

This is the highest-leverage backend module. Most business richness belongs here, not in API routes.

#### `planner.py`

Owns orchestration.

Interface:

```python
plan(problem: PlanningProblem, solver: SolverAdapter) -> PlanningResult
diagnose(problem: PlanningProblem) -> DiagnosticReport
```

Flow:

1. validate schema;
2. validate semantics;
3. normalize;
4. compile to planning graph;
5. call solver adapter;
6. translate solution to plan blocks, ledger, objective explanation, and diagnostics.

#### `ports.py`

Defines solver and persistence seams only when there are real adapters.

```python
class SolverAdapter(Protocol):
    def solve(self, graph: CompiledPlanningGraph, budget: SolveBudget) -> SolverResult: ...
```

At least two adapters make the seam real:

- CP-SAT adapter;
- in-memory/greedy adapter for fast validation and deterministic tests.

#### `adapters/cpsat.py`

Owns OR-Tools-specific lowering.

Responsibilities:

- interval variables;
- optional intervals;
- no-overlap;
- cumulative constraints if later needed;
- alternative selection;
- precedence/wait constraints;
- inventory event constraints;
- objective terms.

No API route or validation module should import OR-Tools directly.

### Persistence architecture

Persistence should store:

- setup/config JSON;
- normalized schema hash;
- inventory lots;
- orders;
- plans;
- plan steps;
- planned ledger events;
- actual ledger events;
- realized step markers;
- locked step markers.

Keep the setup payload as JSON for flexibility, but persist operational records in queryable tables once planning history matters.

Initial persistence can remain in SQLite. The design should not assume SQLite-specific JSON behavior in core modules.

### API architecture

API routes should stay thin:

```text
request -> Pydantic request model -> planner module -> response model
```

Target routes:

```text
GET    /api/universal/templates
POST   /api/universal/configs
GET    /api/universal/configs/{id}
POST   /api/universal/configs/{id}/validate
POST   /api/universal/configs/{id}/generate-data
POST   /api/universal/configs/{id}/plan
POST   /api/universal/configs/{id}/diagnose
POST   /api/universal/configs/{id}/auto-realize
POST   /api/universal/configs/{id}/import-mes
POST   /api/universal/configs/{id}/lock-plan
```

The current bridge to `PlanningInput` can remain while the item-function compiler is introduced.

## Performance strategy

### Compile-time pruning

Do as much work as possible before solver variable creation:

- expand tag inheritance once;
- pre-index inventory by item/location/tag signature;
- pre-index resources by capability and tag;
- precompute state transition candidates;
- drop dominated production paths;
- cap alternatives per demand item;
- cap state transition candidates per pair;
- cap resource candidates per capability requirement;
- prune paths that cannot meet expiry/deadline windows.

### Graph indexes

Use indexes in normalized/compiled structures:

```text
items_by_id
locations_by_id
tags_by_id
resources_by_capability
resources_by_tag
inventory_by_item_location
production_paths_by_output_item
state_candidates_by_resource_state_pair
```

### Incremental replanning

Replanning should:

- preserve realized steps;
- preserve locked future steps;
- discard unlocked future plan steps;
- start from actual ledger at `now`;
- reuse compiled setup if schema hash is unchanged;
- reuse state transition candidate cache if resource graph hash is unchanged.

### Solver budgeting

Expose plan budgets:

```json
{
  "max_seconds": 10,
  "max_paths_per_item": 20,
  "max_resources_per_capability": 30,
  "max_state_transition_candidates": 3
}
```

Diagnostics should report when pruning affects completeness.

## Correctness invariants

The planner must enforce:

1. No non-infinite item inventory goes negative.
2. Inventory lots used by a step match item selector, location, tags, and expiry at consumption time.
3. Resource intervals do not overlap for the same resource.
4. Step outputs appear only after step completion.
5. Inline step wait policies are respected.
6. Resource state requirements are satisfied by initial state, prior steps, or inserted transitions.
7. Storage limits are respected unless set to `-1`.
8. Expired inventory cannot satisfy usable demand.
9. Locked plan steps are not moved.
10. Realized plan steps are immutable execution facts unless explicitly corrected by import.
11. Objective item consumption is explainable by step, order, resource, or transition.
12. Tag exclusive groups do not conflict in inventory lots, resources, or produced outputs.

## Diagnostics requirements

Every infeasibility should point to a business reason:

- missing item source;
- insufficient inventory;
- no resource provides capability;
- resource exists but calendar unavailable;
- selector too restrictive;
- expiry impossible;
- storage limit exceeded;
- state transition unreachable;
- formula invalid;
- all alternatives pruned;
- deadline impossible under finite capacity.

Diagnostics must include:

- affected order/item/step;
- relevant selector;
- candidates considered;
- reason rejected;
- suggested fix.

## Frontend implications

Applied app navigation:

```text
Business resources / Items / Resources / Locations
---
Order
Inventory
Plan
```

APS Studio should provide advanced configuration areas:

1. Items
2. Tags
3. Locations
4. Capabilities
5. Resources
6. Resource state graphs
7. Production paths
8. Affinity rules
9. Calendars
10. Objective/accounting items
11. Sample data
12. Validation and compile diagnostics

The applied pages should feel hand-built:

- dropdowns for references;
- tag pickers with inheritance preview;
- inventory lot grouping by item/location/expiry/tags;
- graph editor for resource states;
- setup matrix UI for common state graph cases;
- production path step editor;
- plan explanation showing item ledger and resource timeline.

## Migration from current implementation

### Current state

The repository currently has:

- fixed `PlanningInput` planner;
- Universal APS config CRUD;
- resource-model demo template;
- bridge compiler only for `discrete_manufacturing_advanced`.

### Migration path

#### Phase 1: documentation and schema

- Add this design document.
- Add `item_function/schema.py`.
- Add schema-only tests for valid/invalid configs.

#### Phase 2: validation and normalization

- Implement tags/selectors/normalization.
- Add diagnostics without solver.
- Add sample item-function discrete manufacturing setup.

#### Phase 3: compiler without full solver

- Compile item-function setup into canonical planning graph.
- Add explainable unsupported-feature diagnostics.
- Add greedy/in-memory adapter for smoke tests.

#### Phase 4: CP-SAT adapter

- Lower compiled graph to CP-SAT.
- Support finite resources, item balance, precedence, wait policies, and deadlines.
- Add objective item minimization.

#### Phase 5: state graph and movement

- Add state transition candidate preprocessing.
- Add location movement steps.
- Add setup/changeover explanation.

#### Phase 6: execution bridge

- Add plan persistence.
- Add lock/unlock.
- Add auto-realize.
- Add MES import placeholder.

## Testing strategy

### Unit tests

Heavy unit coverage for:

- tag expansion/conflicts;
- selector matching;
- inventory stacking;
- expiry;
- formula validation;
- state graph candidate generation;
- ledger projection;
- production path expansion;
- dominance pruning.

### Integration tests

End-to-end planning scenarios:

- make from inventory;
- buy with MONEY;
- outsource with MONEY + material;
- scrap disposal forced by storage limit;
- failed QA rework/disposal;
- movement from warehouse to line;
- no-wait and bounded-wait path;
- setup/state transition from product C to product A;
- locked plan replan stability;
- auto-realize elapsed plan.

### Property-style checks

For generated scenarios:

- item conservation;
- no resource overlap;
- no expired lot used;
- no invalid tag conflict;
- all output lots stack deterministically;
- objective explanation sums to objective total.

## Open design decisions

1. Exact formula language and numeric type: integer, decimal, or rational.
2. Whether locations are required on all inventory lots in v1 or defaulted to one global location.
3. Whether resource travel is implicit in v1 or explicit from the start.
4. How much of RRULE to implement initially.
5. How to represent substitute items: tag selectors first, explicit substitute graph later.
6. Whether safety stock is always a pseudo-order or a first-class inventory policy compiled to pseudo-orders.
7. How to expose Pareto state-transition candidates in UI without overwhelming users.

## Final architecture principle

The backend should not accumulate business-specific planner branches such as:

```text
if template == manufacturing
if template == warehouse
if concept == operation
```

Instead:

```text
validate setup
normalize tags/selectors/calendars/state graphs
compile item-function problem
solve canonical planning graph
explain result
```

That is the deep module seam. It maximizes reuse, keeps correctness local, and lets user data define business logic without constantly changing the APS meta-model.
