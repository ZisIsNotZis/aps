# Unified APS Model — All-in-One Specification

> **Authority**: This document is the single source of truth for the APS kernel.
> Supersedes: `docs/item-function-aps-decision-register.md`, `docs/discrete-factory-rule-catalog.md`, `docs/item-function-aps-architecture.md`, `proposal.md`.
> 
> **Status**: Canonical. All other documents are reference-only or historical.

---

## 1. Philosophy

APS is a **deterministic, integer-only, timed entity-transformation system**.

- Everything is an entity with flat key/value properties.
- Entities are transformed by rules: consume some entities, produce others, occupy time.
- The planner chooses which rules to execute, when, with what batch quantity, and on which equipment.
- The objective is to **maximize money** (or minimize losses, equivalently).
- Uncertainty is not modeled in planning. Realized execution differences are imported as corrections and trigger replanning.

---

## 2. Unified Entity Model

### 2.1 Any entity is a flat object

```yaml
{type: steel_kg, location: plant_a, expiry: 2026-08-20T00:00:00+08:00, value: 500, price: 650}
```

`expiry` stores an absolute datetime. Only in `$` expressions (set/comparison) can `$now` appear — e.g. `expiry: $now+30d` in a produce block compiles to an absolute datetime at compile time. The entity record itself always holds a concrete datetime; `$now` is never stored, only resolved during compilation.
```

### 2.2 Reserved fields

The engine only cares about three reserved fields: `expiry`, `lifetime`, and `datetimeexpr`. All other fields are opaque key/value properties used for matching — they have no special engine semantics.

**Important**: `type`, `location`, `state`, `value`, `price`, and `held_by` are NOT reserved — they are merely conventional. A `consume` selector can match on ANY field, not just `type`. For example:

```yaml
consume:
  - {function: x}  # matches any entity where x ∈ entity.function (list membership)
```

This means "select entities whose `function` list contains `x`". No `type` field is required in the selector.

| Field | Type | Meaning |
|---|---|---|
| `type` | string | Identity — conventionally used for matching |
| `location` | string | Where the entity is |
| `state` | string | Current state of stateful reusable entities |
| `value` | integer | Virtual internal value per unit (for expiry/loss calculations) |
| `price` | integer | Virtual replacement/acquisition cost per unit |
| `held_by` | string | Which equipment instance holds this WIP (internal to a machine) |

**Reserved fields** (engine auto-adds preconditions, see §4):

| Field | Type | Engine behavior |
|---|---|---|
| `expiry` | timestamp | Auto-guard: `$expiry > $now` |
| `lifetime` | integer | Auto-guard: `$lifetime > 0` |
| `datetimeexpr` | string | Auto-guard: `$datetimeexpr.match($now)` |

### 2.3 Units are encoded in type identity

`steel_kg`, `phone_each`, `money_cent` — the engine has no separate unit system.

### 2.4 Matching is QBE (Query By Example)

A consume selector is a partial object. All specified keys must match; unspecified keys are ignored.

```yaml
consume:
  - {type: steel_kg, location: plant_a}  # matches any steel_kg at plant_a, regardless of expiry value
```

**Matching semantics**:

| Entity field type | Query value type | Meaning |
|---|---|---|
| scalar | scalar | Equality (`entity.field == query.value`) |
| list | scalar | Contains (`query.value in entity.field`) |
| list | list | Intersection non-empty (`any(v in entity.field for v in query.value)`) |
| scalar | list | `entity.field in query.value` |

When a query value is a string starting with `$`, it is parsed as an expression:
- `$this` — the current entity being matched
- `$this.<field>` — a field on the current entity
- `$<name>` — a reference to another entity bound by name in the same rule
- `$now` — the current time at evaluation

Example: `{lifetime: $this.max_lifetime}` matches entities whose `lifetime` equals their own `max_lifetime` field.
```

---

## 3. Rule Shape

### 3.1 Core rule structure

```yaml
rule_id:
  batch_min: 1          # default
  batch_max: 100        # max units per execution
  consume:              # × batch quantity
    input_key:
      type: bun_top
      num: 1            # default
  consume_batch:        # once per execution
    crew:               # ⬅ "crew" is a temporary name bound to the item selected by this selector
      type: boh_crew
    glove:
      type: disposable_glove
      num: 2
  duration_s: 5         # seconds per unit (× batch)
  duration_batch_s: 10  # seconds once per execution
  produce:              # × batch quantity
    burger:
      type: burger
      expiry: $top.expiry
  produce_batch:        # once per execution
    crew:               # ⬅ exact name match with consume_batch:crew → inherits all fields (name, age, …)
                        #    If the name did NOT match, this would be a NEW entity with all fields lost.
      lifetime: $x-1
    glove_waste:
      type: disposable_glove_waste
      num: 2
```

### 3.2 Field semantics

| Field | Multiplied by batch qty | Purpose |
|---|---|---|
| `consume` | Yes | Per-unit inputs (materials, components) |
| `consume_batch` | No | Per-execution inputs (crew, equipment, gloves) |
| `produce` | Yes | Per-unit outputs (products, co-products) |
| `produce_batch` | No | Per-execution outputs (state tokens, waste) |
| `duration_s` | Yes | Per-unit processing time |
| `duration_batch_s` | No | Fixed setup/teardown time per execution |

### 3.3 Equipment and state transitions

Equipment is consumed and produced via `consume_batch`/`produce_batch`. State changes are explicit:

```yaml
fry_machine_on:
  consume:
    fry_machine: {type: fry_machine, state: off}
  produce:
    fry_machine: {type: fry_machine, state: on}
  duration_s: 600
```

### 3.4 Attribute references ($ expressions)

Whitelisted fields support bounded expressions:

```yaml
produce:
  burger:
    expiry: min($top.expiry, $bottom.expiry, $stake.expiry)
produce_batch:
  crew:
    lifetime: $x-1
```

**Allowed constructs**: `$start`, `$end`, `$self.<field>`, bound names, integer literals, `+ - * /`, `min max ceil floor`, comparisons (`= != < <= > >=`), logic (`and or not`).

**Implementation strategy**: The expression DSL is designed to be trivially convertible to a safe Python `lambda` — no custom parser or runtime is needed. Each `$` expression compiles to a Python expression with bound variable names, evaluated in a restricted environment with only `min`, `max`, `ceil`, `floor` and arithmetic operators available. Example:

```
$expression: min($top.expiry, $bottom.expiry)
# → lambda top, bottom: min(top['expiry'], bottom['expiry'])
```

**Forbidden**: loops, recursion, user functions, I/O, dynamic code execution, randomness.

---

## 4. Auto-Preconditions

The engine automatically adds precondition guards on three reserved fields if they exist on an entity. These behave as if manually written in the consuming rule:

```yaml
# If entity has expiry field:
$expiry > $now

# If entity has lifetime field:
$lifetime > 0

# If entity has datetimeexpr field:
$datetimeexpr.match($now)
# "datetimeexpr" is a timetable expression — a cron or RRULE-like string
# that defines when the entity is available for consumption.
```

These are **hard constraints**: a consuming rule cannot select an entity that fails any of these guards.

---

## 5. Orders (Requirements)

An order is a requirement for a collection of items with specific conditions, plus a deadline.

```yaml
order:
  id: ORD-1001          # regular business field — not used by the engine for matching or identity
  consume:              # same selector semantics as rule consume: blocks
    finished_phone:
      type: phone_v1_released_each
      location: shipping
      num: 1000
  deadline: 2026-07-30T17:00:00+08:00
  early_delivery_bonus_per_s: 0    # money_cent per second early
  late_delivery_penalty_per_s: 100  # money_cent per second late
```

### 5.1 Order semantics

- `consume` uses the same entity selector semantics as `consume` in rules.
- Multiple requirements in one order are AND — all must be fulfilled.
- The order is fulfilled when all required entities of the specified type/condition exist at or before `deadline`.
- `early_delivery_bonus_per_s` rewards completion before deadline.
- `late_delivery_penalty_per_s` penalizes completion after deadline.
- An order with no deadline is infinite-horizon (no lateness penalty).

### 5.2 Release gate

If the order has an explicit `release_at` timestamp, production for this order may not begin before that time. This is implemented as a production authorization token:

```yaml
inventory:
  - {type: order_1001_release_authorization, quantity: 1, available_at: $release_at}
```

---

## 6. Objective: Money-Based

### 6.1 Core principle

**Everything translates to money.** The objective is always to maximize net money (or equivalently, minimize total losses):

```yaml
objective:
  maximize: $money_cent_remaining   # a $expression, not just an enum — can reference any term

# Optional: expiry-decay controls how fast expiry losses decay as the deadline approaches.
# decay_factor: 0 means full loss at expiry; 1.0 means full loss from the moment of production.
# This is a tunable parameter that shapes how aggressively the solver avoids near-expiry inventory.
expiry_loss_decay_factor: 0.5
```

### 6.2 Objective terms

The solver minimizes a weighted sum of these terms, all normalized to money:

| Term | Source | How it's money |
|---|---|---|
| **Direct cost** | `money_cent` consumed by rules | Purchase cost, labor, energy, disposal |
| **Lateness penalty** | `order.late_delivery_penalty_per_s × seconds_late` | Lost revenue, contract penalties |
| **Early delivery bonus** | `order.early_delivery_bonus_per_s × seconds_early` | Customer incentives |
| **Expiry loss** | Remaining qty at expiry × `entity.value` | Material write-off |
| **End-of-horizon expiry risk** | Remaining qty at horizon × `entity.value × risk_fraction` | At-risk inventory |
| **Inventory holding cost** | `storage_cost_items_per_second × quantity × seconds_held` | Warehousing, capital cost |
| **Setup/changeover cost** | Consumed `money_cent` or `consumables` in transition rules | Tooling, cleaning, waste |
| **Stability penalty** | Deviation from prior plan × configured coefficient | Disruption, replanning cost |
| **Makespan** | Total plan duration × coefficient | Indirect cost proxy |

### 6.3 Expiry and end-of-horizon risk

An entity expiring within the planning horizon incurs **full value loss** on remaining quantity at expiry time.

An entity expiring after the horizon incurs a **fractional loss** based on a finite risk table:

```yaml
expiry_loss_fraction:
  - expires_during_plan:                {numerator: 1, denominator: 1}
  - expires_within_after_plan: 7d       {numerator: 3, denominator: 4}
  - expires_within_after_plan: 30d      {numerator: 1, denominator: 2}
  - expires_later:                      {numerator: 1, denominator: 10}
```

The compiler selects exactly one band and converts it to a fixed integer coefficient before solving.

### 6.4 Objective profile

Multiple profiles exist for different business priorities, expressed as weight multipliers on the terms above:

| Profile | Emphasis |
|---|---|
| `balanced` | Equal weights across all terms |
| `cost_focus` | Higher weight on direct cost, lower on service |
| `service_focus` | Higher weight on lateness/stability, lower on direct cost |

---

## 7. Replanning and Lock Semantics

### 7.1 Completed operations

A completed operation is a historical fact. Its consumed entities are gone, its produced entities exist in inventory, and it no longer appears as a decision variable.

### 7.2 Started/locked operations

A started (or locked) operation becomes:
- Fixed equipment unavailability until its confirmed end
- Fixed future output inventory at that end
- Imported realized consumption

### 7.3 Freeze fence

A time fence. Any prior approved operation starting within the fence is automatically locked. Operations outside the fence remain movable.

### 7.4 Stability penalty

For each prior operation that retains its identity across replanning cycles:

```python
stability_penalty = (
    abs(new_start - old_start) * move_penalty_per_hour
    + (equipment_changed ? equipment_change_penalty : 0)
)
```

### 7.5 Delta limit (optional)

A hard bound on the number of operations that may change assignment or timing between plan versions.

---

## 8. Holding Rules

Entities can carry holding rules that define ongoing costs or constraints:

```yaml
holding_rules:
  glove_waste:
    item: {type: glove_waste}
    max: 10                    # storage limit
                                # ⬆ When inventory hits this limit and glove_waste is still being produced,
                                # the engine is FORCED to consume it via the only available disposal rule
                                # (e.g. glove_waste → money, or glove_waste + money → nothing).
                                # This is "push"-based planning: the constraint triggers consumption,
                                # unlike "pull"-based planning where orders drive production.
  fry_machine:
    item: {type: fry_machine, state: on}
    consume:                  # ongoing consumption while idle, per duration unit
      electricity_kwh: 10
    duration: 1h              # consumption rate period (consume this much every 1 hour)
  crew_salary:
    item: $x.match('.*_crew')
    consume:
      money_cent: 1000
    duration: 1h
```

### 8.1 Hold semantics

- `max`: Hard upper bound on inventory quantity of this entity type.
- `consume` + `duration`: Continuous consumption charged per `duration` period the entity exists in inventory. The `consume` block uses the same selector semantics as rules.
- Entity matching supports `$x.match(regex)` for pattern-based grouping.

---

## 9. Coverage of the A–L Rule Families

| Family | Coverage | Notes |
|---|---|---|
| **A) Material & inventory** | Full | Receipt, putaway, reservation, safety stock, substitution, merge, split, expiry — all via entity identity, rules, and auto-preconditions |
| **B) Movement & logistics** | Full | Location change via consume/produce; capacity-constrained via equipment occupation |
| **C) Production transformation** | Full | Assembly, yield/scrap, co-product, re-entrant, alternate routing, transfer batch — all via rules |
| **D) Resource capability** | Full | Equipment type matching, state, batch capacity, crew size, certification |
| **E) Calendar & shift** | Full | `datetimeexpr` field + auto-precondition; availability windows expanded at compile time |
| **F) Setup & state transition** | Full | Explicit state-to-state rules; equipment consumed and produced with new state |
| **G) Quality & compliance** | Full | Inspection gate, hold/release, rework, scrap, segregation — all via entity state chains |
| **H) Procurement & outsourcing** | Full | Money → entity rules; supplier as equipment type; multi-step outsource flows |
| **I) Maintenance & reliability** | Full | PM rules, `lifetime` decrement via `$x-1`, state-based degradation |
| **J) Order & fulfillment** | Full | Order structure with `consume`, `deadline`, early/late penalties |
| **K) Replanning & lock** | Full | Completed/locked/freeze fence semantics; stability penalties |
| **L) Objective composition** | Full | Money-based; all terms translate to money; configurable profiles |

---

## 10. The 8 Remaining Hard Cases

These cannot be represented losslessly by the current primitives alone:

| # | Hard Case | Why It's Hard | Candidate Primitive |
|---|---|---|---|
| 1 | **Calendar-overlap cost** | Cost depends on where an execution interval overlaps priced calendar windows (overtime). | Integer cost per occupied tick on finite availability intervals |
| 2 | **Resumable execution** | 8h operation spanning shift boundary — pauses and resumes without repeating setup. | Working-tick duration or explicit progress-state segments |
| 3 | **Traceability propagation** | Output entities don't automatically retain selected keys from input entities (supplier_lot, heat). | Allowlisted `copy_from_consume` with explicit key list |
| 4 | **Resource-local cumulative counters** | Runtime/cycle/condition counters that increment across many rules and reset on maintenance. | Bounded integer fields on reusable state tokens with add/subtract/reset |
| 5 | **Allocation fairness** | Max-min fill rate across customer segments — independent linear penalties don't guarantee fairness. | Integer-scaled global fairness constraint with staged optimization |
| 6 | **Cross-plan execution matching** | Stability semantics when prior operations split/merge/rebatch — no one-to-one identity. | Quantity-aware minimum-cost matching at plan load time |
| 7 | **Aggregate grouping** | Cumulative pricing/lead-time tiers across multiple executions in one period. | Finite execution group with aggregate quantity and tier selection |
| 8 | **Age-triggered state transition** | Fresh → degraded at `produced_at + 7d` — expiry can invalidate but can't auto-convert. | Relative timed state-transition event tied to lot creation |

---

## 11. Compiler Sugar (Optional, Not Semantic Gaps)

These are convenience syntaxes that compile losslessly to the finite model:

| Sugar | Expands to |
|---|---|
| `duration_s = batch_duration + unit_duration × q` | One fixed-duration rule per permitted batch quantity |
| `consume_during[]` / `produce_during[]` | Staged rules with intermediate entities |
| Per-instance equipment-state shorthand | One identity-specific state token and rule per instance |

---

## 12. Integer Discipline

- All engine quantities, time ticks, capacities, and objective coefficients are integers.
- External decimal values are converted via explicit scaling and ceiling at configured precision.
- Batch quantity is an integer multiplier of the complete consume/produce vector.
- Time is converted to integer solver ticks. Duration is either fixed-cycle or quantity-linear (via expansion).

---

## 13. Calendar and Availability

Calendars define when equipment/workers are available. They are expanded into finite availability intervals at compile time:

```yaml
equipment_availability:
  - equipment: cnc_1
    intervals:
      - {start: 2026-07-27T08:00:00, end: 2026-07-27T17:00:00}
```

The `datetimeexpr` field on an entity works as an auto-precondition: the entity is only available for consumption if the current time matches its timetable expression.

Planned downtime subtracts intervals before solving:

```yaml
equipment_unavailability:
  - equipment: cnc_1
    start: 2026-08-05T09:00:00
    end: 2026-08-05T13:00:00
```

---

## 14. Summary of the Meta-Model

```
┌─────────────────────────────────────────────────────┐
│                   Planning Session                    │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │  Rules   │  │  Orders  │  │  Initial Inventory │  │
│  │ (entity  │  │ (entity  │  │  (entity qty,      │  │
│  │  transf.)│  │  demand) │  │  expiry, location) │  │
│  └────┬─────┘  └────┬─────┘  └─────────┬──────────┘  │
│       │             │                   │             │
│       ▼             ▼                   ▼             │
│  ┌────────────────────────────────────────────────┐  │
│  │              Solve Engine (CP-SAT)              │  │
│  │  • Entity conservation                         │  │
│  │  • Capacity (no-overlap)                       │  │
│  │  • Calendar compliance                         │  │
│  │  • Precedence (deps, no-wait)                  │  │
│  │  • State transitions                           │  │
│  │  • Objective: maximize money                   │  │
│  └────────────────────────────────────────────────┘  │
│       │                                               │
│       ▼                                               │
│  ┌────────────────────────────────────────────────┐  │
│  │                Result: Plan                     │  │
│  │  • Scheduled blocks (what, when, by whom)      │  │
│  │  • Inventory ledger                             │  │
│  │  • Order outcomes (lateness, cost)              │  │
│  │  • Objective explanation                        │  │
│  │  • Diagnostics                                  │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### The core loop

1. **Define** entities, rules, orders, initial inventory, and equipment.
2. **Compile** to a finite planning graph (expand alternatives, prune dominated paths, generate state transition candidates).
3. **Solve** with CP-SAT (or other solver adapter): choose which rules execute, when, with what batch quantity, on which equipment.
4. **Explain** the result: order outcomes, cost breakdown, bottleneck analysis, inventory ledger.

---

## 15. Document History

| Date | Change |
|---|---|
| 2026-07-24 | Initial unified specification merging decision register, rule catalog, proposal, and code implementation |
