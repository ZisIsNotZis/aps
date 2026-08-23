# Finite APS Kernel Spec and Decision Register

## Authority and scope

This is the single source of truth for APS kernel semantics.

- `docs/discrete-factory-rule-catalog.md` is illustrative coverage and hard-case evidence.
- `docs/item-function-aps-architecture.md` is transitional structural context only.
- If any document conflicts with this file, this file wins.

## Final conclusions so far

1. APS is a deterministic, integer-only timed transformation system.
2. The kernel does not fundamentally distinguish worker/machine/tool/material; all are entities with properties.
3. Matching is primarily QBE (partial object match), with restricted expressions allowed in whitelisted fields.
4. Uncertainty is not modeled in planning rules; realized execution differences are imported as corrections and trigger replanning.
5. Most industrial scenarios are representable with finite rule expansion; only a bounded set of unresolved primitives remains.

## Accepted kernel model

### 1) Unified entity model

- Any planning object is an entity with flat key/value properties.
- Common reserved fields include:
  - `type`
  - `location`
  - `state` (for stateful reusable entities)
  - `value` (virtual internal value per unit)
  - `price` (virtual external replacement/acquisition cost per unit)
- Units are encoded in `type` identity (for example `steel_kg`, `phone_each`, `money_cent`).

### 2) Rule shape

Each executable rule has:

- `batch` (`min`, `max`, optional `multiple`)
- `consume_batch` (once per execution)
- `consume` (scaled by selected batch quantity)
- `produce` (scaled by selected batch quantity)
- `produce_batch` (once per execution)
- time terms (`time_batch_s`, `time_s` or compiled equivalent fixed duration)

Legacy aliases (`consume_per_batch` / `produce_per_batch`, `duration`) may remain as compile-time synonyms.

### 3) Binding and identity

- A reusable selected entity may be locally bound (for example `processor`).
- Produced entities may reference that binding (for example `held_by: processor`) to preserve same-instance identity.
- This is how internal WIP, blocking, and uninterrupted multi-stage runs are modeled without machine-specific hardcoding in the rule selector.

### 4) State transitions

- Stateful reusable entities transition via rule execution:
  - required input state
  - resulting output state
- Explicit directed transitions are required; no implicit `state != X` semantics.
- Recommended modeling:
  - `rested -> tired -> very_tired`
  - work rules simply do not accept `very_tired`.

### 5) Expiry and relative lifetime

- Existing inventory may carry absolute `expires_at`.
- Produced entities may carry relative `expires_after`.
- `expires_after: 0` encodes no-wait continuation.
- Expiry invalidates consumption after deadline; expiry alone never resets/cleans stateful reusable entities.

### 6) Value/price economics

- Every compiled item/entity has integer `value` and `price`.
- `value` is used for inventory-loss style objective terms (including expiry loss).
- `price` describes replacement economics, even for normally non-buyable entities.
- `price` does not create procurement automatically; procurement still needs explicit transformation rules.

### 7) Deterministic yield

- Statistical behavior is compiled to deterministic integer vectors.
- Example: `100 -> 98 accepted + 2 rejected`.
- Batch quantity is an integer multiplier of the full vector.

### 8) Integer discipline

- Engine-side quantities, time ticks, capacities, and objective coefficients are integers.
- Conversion from external decimals uses explicit scaling and ceiling at chosen precision.

### 9) Goals, locks, and objective terms

- Goals, release/due windows, required executions, freeze constraints, and stability terms are planning-session structures.
- Objective terms are finite compiler-known integer terms; no arbitrary runtime objective callbacks.

## Restricted expression DSL (accepted)

Expressions are allowed, but only as a bounded DSL in whitelisted fields.

### Whitelisted use

- relative time fields (`expires_after`, deadline/lifetime checks)
- bounded numeric updates (for example lifetime decrement)
- selected objective/config terms
- optional rule guards that compile to finite constraints

### Allowed constructs

- references: `$start`, `$end`, `$self.<field>`, bound names
- literals: integers, durations
- operators: `+ - * /`
- comparisons: `= != < <= > >=`
- logic: `and or not`
- bounded helpers: `min max ceil floor`

### Forbidden constructs

- loops, recursion, user-defined functions
- external I/O
- dynamic code execution
- randomness/stochastic sampling
- unbounded iteration or data-dependent graph expansion at solve time

## Rejected paths

1. **Open formula engine as primary semantics**  
   Rejected due to safety, explainability, and solver-lowering uncertainty.
2. **Uncertainty in rule execution outcomes**  
   Rejected. Planning remains deterministic; variance is imported post factum.
3. **Mandatory FEFO as universal hard constraint**  
   Rejected as default. Expiry/risk is modeled as hard validity + value-based loss tradeoffs.
4. **Automatic broad key propagation from consume to produce**  
   Rejected as implicit default. Any copy semantics must be bounded/allowlisted.
5. **Hard split by class (worker/equipment/item) in kernel semantics**  
   Rejected. Kernel is unified entity transformation; class labels are domain/UI vocabulary.

## Results achieved

1. Procurement/inbound rules normalized to finite deterministic forms.
2. `consume_batch`/`produce_batch` symmetry established for fixed per-execution effects.
3. Relative expiry successfully subsumed no-wait and bounded-wait handoffs.
4. Mobile reusable resource movement represented with identity-preserving produce/consume batch semantics.
5. Quality, rework, outsourcing, setup, and most movement cases mapped losslessly with finite expansions.
6. Hard cases isolated into a bounded unresolved list.

## Open decisions (genuine remaining hard cases)

1. **Calendar-overlap cost and resumability**  
   Charging execution overlap across priced windows and pause/resume semantics across unavailable windows.
2. **Traceability propagation**  
   Exact allowlisted `copy_from_consume` and multi-parent lineage policy.
3. **Resource-local cumulative counters**  
   Runtime/cycle/tool-life/condition bounded updates and reset semantics.
4. **Global goal fairness**  
   Max-min style fill-rate guarantees across segments with integer-scaled staged optimization.
5. **Cross-plan execution matching**  
   Stability semantics when prior executions split/merge/rebatch.
6. **Aggregate identity and indivisibility**  
   All-or-none routing for approved requisitions/traceable lots.
7. **Aggregate commercial grouping**  
   Period/day-level cumulative pricing/lead-time tiers across multiple executions.
8. **Age-triggered state transition**  
   Automatic deterministic conversion to degraded identities at relative ages.

## Optional compiler sugar (not semantic blockers)

These are convenience syntax candidates because they are losslessly expandable:

1. quantity-linear duration declarations (`time_batch_s + time_s * q`) as sugar over finite expansion;
2. timed material event lists (`consume_during[]`, `produce_during[]`) as sugar over staged rules;
3. per-instance equipment-state shorthand as sugar over generated identity-specific rules.

## Documentation policy

1. Add or change semantics here first.
2. Reflect each semantic change with at least one concrete industrial example in `discrete-factory-rule-catalog.md`.
3. Keep structural/compiler implementation notes in `item-function-aps-architecture.md` only after they align with this file.
