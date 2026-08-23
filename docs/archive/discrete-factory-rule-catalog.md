# Discrete Manufacturing Rule Catalog (Rule-Driven APS)

## Purpose

This document makes the rule-driven direction explicit for a **typical discrete manufacturing factory**.  
It enumerates the practical rule families needed to model most day-to-day planning behavior.

Scope is factory planning (APS), not full MES execution detail.

Authoritative semantics live in `docs/item-function-aps-decision-register.md`. This document is the industrial example/evidence companion.

## Finite rule model

An executable rule uses only a restricted finite structure:

```yaml
- id: rule_id
  equipments:
    - bind: selected_equipment
      function: required_function
      state: required_state
      state_after: resulting_state
  batch:
    minimum: 1
    maximum: 100
  consume_per_batch: []
  consume: []
  produce: []
  produce_per_batch: []
  duration: 1h
```

- consume-side items and equipment requirements are partial flat-object selectors;
- an equipment requirement may bind the selected instance locally and transform its finite `state`;
- produced items are explicit flat objects;
- proportional lists scale with the selected integer batch quantity;
- per-batch lists occur once per execution;
- duration and every quantity are integers at engine precision;
- optional expressions are allowed only in whitelisted fields via the restricted DSL defined in the decision register.
- no loops, dynamic code execution, callbacks, randomness, or open-ended runtime constraint arrays exist.

Goals, finite calendar windows, required executions, and compiler-known integer objective terms are planning-session data outside the transformation body.

The A–L lists below are a **coverage checklist**, not canonical syntax. Their detailed finite representations and unresolved gaps appear in Sections 1–13.

---

## A) Material and inventory rules

1. **Receipt rule**  
   PO/inbound creates inventory lot at receiving location with tags/expiry.
2. **Putaway rule**  
   Receiving/staging lot moves to storage location.
3. **Reservation rule**  
   Inventory quantity reserved for order/program, unavailable to others.
4. **Allocation rule**  
   Reserved lot assigned to a specific downstream step.
5. **Safety stock guard rule**  
   Prevent consumption that would breach configured floor.
6. **Substitution rule**  
   Alternate material allowed when selector/quality/spec conditions hold.
7. **Lot merge rule**  
   Lots stack only if item/location/expiry/tags exactly match.
8. **Lot split rule**  
   One lot split into multiple downstream lots with trace tags.
9. **Expiry exclusion rule**  
   Expired/near-expiry lots blocked unless explicit override path exists.
10. **Shelf-life decay rule**  
    Effective quality state changes with time/storage conditions.

---

## B) Movement and logistics rules

1. **Intra-cell move rule**  
   Optional zero-time/zero-cost move (or small fixed lag).
2. **Intra-plant move rule**  
   Move between work centers/warehouses with handling time and transporter occupation.
3. **Inter-warehouse transfer rule**  
   Truck/dock/calendar-constrained transfer with lead time and cost.
4. **Dock capacity rule**  
   Loading/unloading slots are finite-capacity resources.
5. **Handling-unit compatibility rule**  
   Some lots require specific forklift/crane/container type.
6. **Move batch rule**  
   Transfer in pallet/container lot sizes only.

---

## C) Production transformation rules

1. **Make/assemble rule**  
   BOM components + capability/resource occupation -> finished/semi-finished output.
2. **Operation sequence rule**  
   Enforce predecessor-successor relation across steps.
3. **No-wait / bounded-wait rule**  
   Intermediate step handoff timing constraints.
4. **Yield/scrap rule**  
   Deterministic output and scrap quantities from input batch.
5. **Co-product/by-product rule**  
   One execution emits primary plus secondary outputs.
6. **Re-entrant routing rule**  
   Item can revisit capability/workcenter under controlled path semantics.
7. **Alternative routing rule**  
   Multiple valid make paths; optimizer chooses by objective/feasibility.
8. **Lot-size execution rule**  
   Min/max/multiple constraints for each operation/path.
9. **Transfer-batch overlap rule**  
   Downstream can start after partial upstream completion threshold.

---

## D) Resource capability rules

1. **Capability provision rule**  
   Resource provides capability at configured rate.
2. **Single-active-assignment rule**  
   Resource executes one active assignment at a time (unless modeled as split resources).
3. **Batch-capacity rule**  
   Resource can process N units in one run.
4. **Qualification/certification rule**  
   Worker/tool cert must match operation requirements.
5. **Tooling/fixture requirement rule**  
   Operation requires both machine and finite secondary tool resource.
6. **Crew-size rule**  
   Operation requires N operators/roles simultaneously.
7. **Affinity modifier rule**  
   Tag combinations adjust effective rate/cost.
8. **Resource eligibility rule**  
   Tag/state/location filters determine valid candidates.

---

## E) Calendar and shift rules

1. **Working calendar rule**  
   Resource only usable in allowed windows.
2. **Exception/downtime rule**  
   Planned maintenance/holiday blocks availability.
3. **Overtime rule**  
   Optional additional windows with premium penalties.
4. **Start/stop window rule**  
   Some steps may start only in specific windows.
5. **Carry-over rule**  
   Step may or may not run across shift boundary.

---

## F) Setup and state-transition rules

1. **Initial state rule**  
   Resource starts in known state.
2. **Changeover transition rule**  
   State A -> B consumes time/cost/consumables.
3. **Sequence-dependent setup rule**  
   Transition depends on previous product/tool family.
4. **Warmup/cooldown rule**  
   Enter/exit thermal/ready states with delays.
5. **Cleaning/sanitization rule**  
   Mandatory transition before specific product classes.
6. **State feasibility rule**  
   Operation requires resource in allowed state set.

---

## G) Quality and compliance rules

1. **Inspection gate rule**  
   Output enters `unchecked`; shipping requires `released`.
2. **Hold/release rule**  
   Lots can be quarantined/released by path/rule.
3. **Rework rule**  
   Failed lots can flow to rework path.
4. **Scrap disposition rule**  
   Failed/scrap lots routed to disposal or salvage path.
5. **Traceability propagation rule**  
   Supplier/lot/batch tags propagate through transformation.
6. **Regulatory segregation rule**  
   Incompatible material classes cannot share storage/equipment windows.

---

## H) Procurement and outsourcing rules

1. **Buy rule**  
   Money -> item with lead time, MOQ, vendor calendar constraints.
2. **Supplier capacity rule**  
   Vendor has finite period capacity.
3. **MOQ/multiple rule**  
   Purchase quantities must satisfy commercial lot constraints.
4. **Outsource operation rule**  
   Semi-finished input + money + transport -> processed output.
5. **Dual-source selection rule**  
   Multiple suppliers/routes with cost/lead-time tradeoff.

---

## I) Maintenance and reliability rules

1. **Preventive maintenance rule**  
   Periodic operation that occupies resource and restores state.
2. **Usage-trigger maintenance rule**  
   Trigger after runtime/cycle thresholds.
3. **Condition degradation rule**  
   Resource condition decays with usage/time.
4. **Repair rule**  
   Failed/degraded resource consumes parts/labor to recover.
5. **Maintenance priority rule**  
   Safety-critical PM can preempt production windows.

---

## J) Order and fulfillment rules

1. **Release rule**  
   Order eligible only after release timestamp.
2. **Due-date penalty rule**  
   Lateness incurs objective penalties.
3. **Early-delivery reward/penalty rule**  
   Optional earliness objective term.
4. **Partial-shipment rule**  
   Allow split fulfillment with milestone constraints.
5. **Priority-class rule**  
   Weighted objective/service policy by customer/order class.
6. **Allocation fairness rule**  
   Optional anti-starvation across order segments.

---

## K) Replanning and execution-lock rules

1. **Completed-lock rule**  
   Realized past steps immutable.
2. **Started-lock rule**  
   In-progress assignments constrained to continue.
3. **Freeze-fence rule**  
   Near-term horizon movement restricted.
4. **Stability penalty rule**  
   Penalize deviations from prior approved plan.
5. **Delta-limit rule**  
   Optional bound on number/magnitude of schedule changes per replan.

---

## L) Objective composition rules

1. **Cost objective rule**  
   Minimize money/utility/tooling/overtime/disposal terms.
2. **Service objective rule**  
   Minimize weighted lateness / maximize due-date hit rate.
3. **Throughput objective rule**  
   Maximize completed quantity in horizon.
4. **Changeover minimization rule**  
   Penalize expensive transitions.
5. **Inventory posture rule**  
   Penalize excess holding and/or stockout risk.
6. **Composite policy rule**  
   Weighted combination by selected planning policy profile.

---

## Practical “99% factory” baseline profile

For most discrete factories, these are the must-have rule families:

1. Make/assemble, alternate routing, lot-size rules.
2. Resource capability + calendar + setup/changeover.
3. Inventory/receipt/reservation/safety-stock.
4. Movement between storage/workcenters.
5. Quality gate + rework + scrap disposition.
6. Buy/outsource with lead time and MOQ.
7. Due-date penalties + priority classes.
8. Replan locks + stability.

If these are implemented well, the model typically covers almost all practical discrete-factory scheduling pain points.

---

## Rule expressions in APS terms (`natural language: APS expression`)

Conversion status:

- Section 1 (Procurement and inbound): finite YAML schema.
- Section 2 (Inventory and material governance): finite through substitution and expiry-aware residual inventory loss.
- Section 3 (Movement and internal logistics): finite through mobile reusable-equipment state using `produce_per_batch`.
- Section 4 (Core manufacturing transforms): finite except transfer-batch output events.
- Sections 5–13: converted to finite rules/session primitives with unresolved cases collected explicitly.

### 1) Procurement and inbound

This section is expressed using a restricted finite language:

- every rule execution chooses one batch quantity `q`;
- all input/output quantities are fixed coefficients multiplied by `q`, or fixed once per execution;
- duration is selected from a finite duration mode;
- executors are reusable capacity providers and are not consumed;
- no arbitrary Boolean expressions, loops, user functions, or general formulas are allowed.

#### Finite vocabulary used here

- Items and equipment are flat key-value objects.
- There is no nested `tags` level.
- A consume-side `item` is a partial-object selector.
- A produce-side `item` is the complete object to create.
- Equipment requirements are partial-object selectors, normally selecting by `function`.
- Item/equipment keys are otherwise opaque to the planner; selector matching only compares key/value equality.
- The planner understands only the finite rule structure: equipment occupation, quantities, batch bounds, and duration.
- The engine has no unit system. Units are encoded into values such as `packed_steel_kg` and `money_cent`.
- Every compiled item carries reserved integer `value` and `price` fields. Authoring may omit them only when deterministic defaults for that exact item type are expanded before the rule reaches the engine.
- `consume[].quantity` and `produce[].quantity` are ratios multiplied by the selected rule batch quantity.
- `consume_per_batch[].quantity` is consumed once per rule execution and is not multiplied by the selected batch quantity.
- `produce_per_batch[].quantity` is produced once per rule execution and is not multiplied by the selected batch quantity.
- The engine accepts integers only. Item quantities, batch bounds, capacities, costs, and internal time ticks are integers.
- Decimal/statistical ratios must be converted into an equivalent integer rule quantum before entering the engine.
- When an external value cannot be represented exactly at the configured precision, it is rounded upward (`ceil`). Configuration may deliberately adjust the ratio/precision to avoid pathological scaling.

#### Base procurement: supplier converts money into delivered packed steel

Natural language: Supplier A accepts 500–6000 kg per purchase batch. Each kg costs 5 money units. The packed steel becomes available in the receiving yard three elapsed days after ordering.

```yaml
rules:
  - id: buy_packed_steel_supplier_a
    equipments:
      - function: supplier_a_steel

    batch:
      minimum: 500
      maximum: 6000

    consume:
      - item:
          type: money_cent
        quantity: 500

    produce:
      - item:
          type: packed_steel_kg
          location: plant_a_inbound_queue
        quantity: 1

    duration: 3d
```

For execution quantity `q=1000 kg`, this rule has exactly:

```text
500000 money_cent -> 1000 packed_steel_kg
```

and occupies one equipment matching `{ function: supplier_a_steel }` for three days. The rule itself limits an execution to 500–6000 batch units.

The rules below are canonical where they use this finite vocabulary. Unresolved cases are retained explicitly and consolidated in **Collected hard cases**.

#### Inbound: dock converts packed steel into usable steel

Natural language: Any equipment providing `inbound_steel` can convert packed steel waiting in Plant A's inbound queue into usable steel in raw-material storage. One execution takes one hour and handles at most 6000 kg.

```yaml
  - id: inbound_packed_steel
    equipments:
      - function: inbound_steel

    batch:
      minimum: 1
      maximum: 6000

    consume:
      - item:
          type: packed_steel_kg
          location: plant_a_inbound_queue
        quantity: 1

    produce:
      - item:
          type: steel_kg
          location: plant_a_raw_storage
        quantity: 1

    duration: 1h
```

For batch quantity `q`:

```text
q packed_steel_kg@plant_a_inbound_queue
  -> q steel_kg@plant_a_raw_storage
```

The selected dock equipment is occupied for one hour. Multiple dock equipment objects may provide `inbound_steel`, so the scheduler may run independent inbound executions concurrently.

Problem encountered: because the consume selector is partial and the produced item is explicit, extra input keys such as `supplier`, `heat`, or `purchase_order` are intentionally not copied. If those keys must survive inbounding, the finite language must choose one of:

1. write separate rules that explicitly select and reproduce each required key combination;
2. add a narrowly defined key-copy operation;
3. declare those keys irrelevant to APS after inbounding.

No automatic copying behavior is added yet.

#### Optional inbound inspection

If inspection is mandatory, inbounding must produce an item that is not yet usable. The inspection rule then converts it into usable steel.

```yaml
  - id: inbound_packed_steel_for_inspection
    equipments:
      - function: inbound_steel

    batch:
      minimum: 1
      maximum: 6000

    consume:
      - item:
          type: packed_steel_kg
          location: plant_a_inbound_queue
        quantity: 1

    produce:
      - item:
          type: steel_awaiting_inspection_kg
          location: plant_a_inspection_queue
        quantity: 1

    duration: 1h

  - id: inspect_inbound_steel
    equipments:
      - function: inspect_inbound_steel

    batch:
      minimum: 1
      maximum: 60

    consume:
      - item:
          type: steel_awaiting_inspection_kg
          location: plant_a_inspection_queue
        quantity: 100

    produce:
      - item:
          type: steel_kg
          location: plant_a_raw_storage
        quantity: 98
      - item:
          type: rejected_steel_kg
          location: plant_a_rejected_storage
        quantity: 2

    duration: 30m
```

The inspection rule uses an atomic integer quantum of 100:

```text
100 steel_awaiting_inspection_kg
  -> 98 steel_kg
   + 2 rejected_steel_kg
```

There is no uncertainty or solver-selected outcome. The configured statistical fractions are the planning truth. Actual execution differences are later inventory corrections from MES/ERP and may trigger replanning.

#### Yield invariants

For a pure classification/split rule such as inspection:

```text
sum(produce.quantity) = sum(consume.quantity)
```

For manufacturing rules that add/remove mass or count through consumables, evaporation, cutting loss, or packaging, conservation is expressed by explicitly producing every relevant output, including scrap/waste.

#### Integer scaling invariant

The engine never accepts floating-point values. A statistical ratio is authored or compiled as the smallest practical integer vector:

```text
0.98 accepted + 0.02 rejected
=> consume 100, produce 98 accepted + 2 rejected
```

The selected batch quantity is an integer multiplier of the whole rule vector. For the example, one batch unit means 100 kg:

```yaml
batch:
  minimum: 1
  maximum: 60
```

An execution with selected batch quantity `q=60` consumes 6000 kg, produces 5880 kg accepted and 120 kg rejected. The same rule structure works for `phone_each`; neither produces fractional inventory.

Time is also converted to integer solver ticks. The configured duration remains a fixed-cycle duration unless the rule explicitly uses a quantity-linear duration mode. Integer normalization must not silently change a fixed 30-minute batch into `30 minutes * quantity`.

If a source ratio or duration cannot be represented exactly:

1. choose a larger integer quantum/tick precision;
2. if that becomes impractical, tune the configured approximation;
3. round the final external-to-engine conversion upward.

Ceiling is applied during conversion to integer quantities/ticks, not independently to every output after execution, because independent output ceilings could create material.

#### Separate transport when transport is capacity-constrained

The base purchase rule above includes delivery in the three-day lead time. If trucks, routes, or docks matter, split procurement from transport.

```yaml
  - id: supplier_prepare_packed_steel
    equipments:
      - function: supplier_a_steel

    batch:
      minimum: 500
      maximum: 6000

    consume:
      - item:
          type: money_cent
        quantity: 500

    produce:
      - item:
          type: packed_steel_kg
          location: supplier_a_shipping
        quantity: 1

    duration: 2d

  - id: transport_packed_steel_to_plant_a
    equipments:
      - function: transport_supplier_a_to_plant_a

    batch:
      minimum: 1
      maximum: 6000

    consume:
      - item:
          type: packed_steel_kg
          location: supplier_a_shipping
        quantity: 1

    produce:
      - item:
          type: packed_steel_kg
          location: plant_a_inbound_queue
        quantity: 1

    duration: 1d
```

The first rule occupies supplier capacity; the second occupies route transport capacity. The item itself carries its location by changing from one explicit item object to another.

If loading and unloading docks must also be occupied, list all required function selectors:

```yaml
    equipments:
      - function: transport_supplier_a_to_plant_a
      - function: load_supplier_a
      - function: unload_plant_a
```

All selected equipment is occupied for the same one-day interval. This is conservative when loading/unloading consume only part of the trip. Modeling their shorter intervals would require separate load, travel, and unload rules, which is still possible without extending the language.

#### Fixed cost per execution

`consume` expresses proportional consumption:

```text
500 money_cent per 1 packed_steel_kg
```

`consume_per_batch` expresses consumption once per rule execution:

```text
10000 money_cent once per purchase order
```

Together:

```yaml
  - id: buy_packed_steel_supplier_a_with_order_fee
    equipments:
      - function: supplier_a_steel

    batch:
      minimum: 500
      maximum: 6000

    consume_per_batch:
      - item:
          type: money_cent
        quantity: 10000

    consume:
      - item:
          type: money_cent
        quantity: 500

    produce:
      - item:
          type: packed_steel_kg
          location: plant_a_inbound_queue
        quantity: 1

    duration: 3d
```

For selected batch quantity `q`:

```text
consume 10000 + 500q money_cent
produce q packed_steel_kg
```

The engine still performs integer arithmetic only. `consume_per_batch` does not introduce formulas; it is a second finite input list with fixed execution multiplicity `1`.

#### Multiple suppliers and expedite options

Natural language: Plant A may buy standard steel from Supplier A or Supplier B, or use Supplier A's expedite service. Each option is a complete rule.

```yaml
  - id: buy_steel_supplier_a_standard
    equipments:
      - function: supplier_a_steel_standard
    batch:
      minimum: 500
      maximum: 6000
    consume:
      - item:
          type: money_cent
        quantity: 500
    produce:
      - item:
          type: packed_steel_kg
          location: plant_a_inbound_queue
        quantity: 1
    duration: 3d

  - id: buy_steel_supplier_b_standard
    equipments:
      - function: supplier_b_steel_standard
    batch:
      minimum: 1000
      maximum: 10000
    consume:
      - item:
          type: money_cent
        quantity: 540
    produce:
      - item:
          type: packed_steel_kg
          location: plant_a_inbound_queue
        quantity: 1
    duration: 2d

  - id: buy_steel_supplier_a_expedite
    equipments:
      - function: supplier_a_steel_expedite
    batch:
      minimum: 500
      maximum: 2000
    consume:
      - item:
          type: money_cent
        quantity: 700
    produce:
      - item:
          type: packed_steel_kg
          location: plant_a_inbound_queue
        quantity: 1
    duration: 1d
```

No rule inherits from another rule and no conditional price or duration exists. The optimizer chooses among explicit transformations.

#### Supplier qualification and material grade

Natural language: Aerospace-grade steel may be purchased only through equipment providing the qualified aerospace procurement function.

```yaml
  - id: buy_aerospace_steel_supplier_a
    equipments:
      - function: supplier_a_aerospace_steel
    batch:
      minimum: 500
      maximum: 6000
    consume:
      - item:
          type: money_cent
        quantity: 800
    produce:
      - item:
          type: packed_steel_kg
          grade: aerospace
          location: plant_a_inbound_queue
        quantity: 1
    duration: 5d
```

The engine does not interpret `aerospace`; the qualified behavior is represented by the selected function and explicit output object.

#### Dock requiring simultaneous labor and forklift

Natural language: Heavy inbound steel simultaneously requires an inbound dock, a heavy-load forklift, and a qualified receiving operator for the complete one-hour execution.

```yaml
  - id: inbound_heavy_steel
    equipments:
      - function: inbound_heavy_steel
      - function: lift_heavy_load
      - function: operate_heavy_load
    batch:
      minimum: 1
      maximum: 6000
    consume:
      - item:
          type: packed_steel_kg
          location: plant_a_inbound_queue
        quantity: 1
    produce:
      - item:
          type: steel_kg
          location: plant_a_raw_storage
        quantity: 1
    duration: 1h
```

All three selected equipment instances are occupied over the same interval. If their intervals differ, loading, movement, and putaway must be separate rules.

#### Dock appointment or delivery window

An externally confirmed appointment is a locked start window for an execution:

```yaml
execution_requirements:
  - id: appointment_po_1042
    rule: inbound_heavy_steel
    batch_quantity: 3000
    start_window:
      earliest: 2026-07-23T09:00:00+08:00
      latest: 2026-07-23T10:00:00+08:00
```

This is instance data, not a new rule type.

#### Partial deliveries

If a 6000 kg purchase may arrive as three independent 2000 kg deliveries, represent it as three executions. The rule remains unchanged:

```yaml
execution_requirements:
  - { id: po_1042_a, rule: buy_packed_steel_supplier_a, batch_quantity: 2000 }
  - { id: po_1042_b, rule: buy_packed_steel_supplier_a, batch_quantity: 2000 }
  - { id: po_1042_c, rule: buy_packed_steel_supplier_a, batch_quantity: 2000 }
```

If the supplier—not the planner—chooses the split unpredictably, exact arrival timing cannot be planned losslessly without confirmed receipt events.

#### Blanket agreement or reserved supplier capacity

Natural language: Supplier A permits at most 20,000 kg of contracted call-off during week 30. Materialize that allowance as a dated consumable item.

```yaml
inventory:
  - item:
      type: supplier_capacity_kg
      supplier: supplier_a
      period: 2026_w30
    quantity: 20000
    available_at: 2026-07-20T00:00:00+08:00
    expires_at: 2026-07-27T00:00:00+08:00
```

The corresponding period-specific purchase rule consumes one quota item per kilogram:

```yaml
  - id: buy_steel_supplier_a_week_30
    equipments:
      - function: supplier_a_steel_standard
    batch:
      minimum: 500
      maximum: 6000
    consume:
      - item:
          type: money_cent
        quantity: 500
      - item:
          type: supplier_capacity_kg
          supplier: supplier_a
          period: 2026_w30
        quantity: 1
    produce:
      - item:
          type: packed_steel_kg
          location: plant_a_inbound_queue
        quantity: 1
    duration: 3d
```

The planning input must explicitly materialize the quota item and rule for every relevant period. `available_at` and `expires_at` prevent capacity from one period being used in another. This stays finite but moves recurring-period expansion outside the rule engine.

#### Quantity-dependent lead time

Natural language: Supplier A delivers 500–2000 kg in two days, but 2100–6000 kg takes three days.

```yaml
  - id: buy_steel_supplier_a_small
    equipments:
      - function: supplier_a_steel_standard
    batch:
      minimum: 500
      maximum: 2000
    consume:
      - item:
          type: money_cent
        quantity: 500
    produce:
      - item:
          type: packed_steel_kg
          location: plant_a_inbound_queue
        quantity: 1
    duration: 2d

  - id: buy_steel_supplier_a_large
    equipments:
      - function: supplier_a_steel_standard
    batch:
      minimum: 2100
      maximum: 6000
    consume:
      - item:
          type: money_cent
        quantity: 500
    produce:
      - item:
          type: packed_steel_kg
          location: plant_a_inbound_queue
        quantity: 1
    duration: 3d
```

These two rules represent the policy losslessly when each execution is a separate purchase order and the supplier permits order splitting. A 6000 kg material requirement may then become three independent 2000 kg purchase orders, each with a two-day lead time. That is not an optimizer exploit; it is a valid procurement decision. `consume_per_batch` can represent any fixed fee charged for each purchase order.

A harder, different policy exists only when the supplier explicitly aggregates orders or an external purchase requirement must remain indivisible:

```text
commercial order identity + aggregate quantity across its executions
```

Examples include “all orders placed on the same day share one cumulative price tier” and “this approved 6000 kg purchase requisition must become one purchase order.” Those policies need one of:

1. require one indivisible procurement execution for each external purchase requirement;
2. add a finite group constraint that sums batch quantities and selects exactly one band;
3. pre-expand complete mutually exclusive purchase-order alternatives outside the engine.

This aggregate-order case is not implied by ordinary quantity-dependent lead time and should be added only when a real commercial contract requires it.

#### Committed purchase orders

Natural language: A 3000 kg purchase order has already been placed and is confirmed to arrive at 09:00 on July 23. Planning no longer decides whether to buy it, so represent it as future inventory rather than another selectable procurement execution.

```yaml
inventory:
  - id: po_1042
    item:
      type: packed_steel_kg
      location: plant_a_inbound_queue
    quantity: 3000
    available_at: 2026-07-23T09:00:00+08:00
```

The payment and supplier decision are historical facts outside the remaining planning horizon. If cancellation or rescheduling is still allowed, it is no longer a committed receipt and must instead be represented by selectable rules or explicit external alternatives.

#### Procurement/inbound problems encountered

1. **“Supplier as equipment” needs precise capacity semantics.**  
   A single executor occupied for three days implies only one overlapping purchase batch. This is correct only if it represents a real supplier capacity lane. Use multiple logical supplier-lane executors or a finite period quota when overlapping orders are allowed.

2. **Periodic supplier quotas require horizon expansion.**  
   Dated consumable quota items preserve the finite transformation language, but an external compiler must materialize each period's item and period-specific rule.

3. **Aggregate commercial policies differ from per-order policies.**  
   Splitting demand into several purchase executions is valid when each execution is a separate permitted order. Indivisible requisitions, cumulative pricing periods, or contracts that aggregate orders require explicit execution-group semantics.

4. **Lead-time meaning must be explicit.**  
   Three elapsed days and three supplier working days are different. The finite language therefore requires `clock: elapsed | working`.

5. **Location as a normal free-form tag is unsafe.**  
   If arbitrary rules may rewrite it, impossible teleportation can be created accidentally. `location` should be a reserved, single-valued, compiler-indexed tag changed only by declared outputs.

6. **Packaging as a new type versus a tag is a modeling choice.**  
   `packed_steel -> steel` is clear and finite. Alternatively, use `type=steel, packaging=packed -> packaging=unpacked`. The second preserves item identity better, but requires tag replacement. Both compile to the same transformation structure.

7. **Planned yield and realized yield are different records.**  
   APS uses the configured deterministic integer output vector. MES may later report different realized quantities, which are imported as corrections and trigger replanning.

8. **Storage capacity is not enforced by the inbound rule itself.**  
   A separate inventory-capacity invariant is required to prevent output from exceeding receiving/raw-storage limits.

9. **Unit conversion is outside the engine.**  
   Values such as `steel_kg` and `steel_tonne` are different item identities. Any conversion between them must be an explicit integer transformation rule.

10. **One-hour dock time may mean fixed-cycle or quantity-dependent processing.**  
    The example uses a fixed one-hour duration for any batch up to 6000 kg. Quantity-dependent timing can use disjoint finite batch bands when separate executions are operationally valid.

11. **Aggregate contracts need explicit grouping.**  
    Non-overlapping rule ranges are sufficient for independent orders. Only policies defined over a requisition, day, contract period, or other aggregate need execution grouping.

12. **Supplier-specific output traceability requires finite tag sources.**  
    Constant output tags are insufficient. The language needs a bounded operation such as `copy_executor_tags`, not general string interpolation.

13. **Partial delivery decisions may belong outside APS.**  
    If the supplier controls the split and dates, APS needs confirmed external execution/receipt data rather than pretending the split is a solver decision.

14. **Calendars do not express period quotas.**  
    A calendar answers *when* an executor may work, not *how much* it may provide during a week. Dated capacity-token lots are the minimal rule-compatible representation.

15. **Several simultaneous capacity providers are supported.**  
    `equipments` is a finite list of selectors; all selected equipment instances share the rule execution interval.

The remaining sections use the same finite language and mark unresolved semantics explicitly.

### 2) Inventory and material governance

This section continues using only integer quantities, explicit item objects, partial consume selectors, and complete produced objects.

#### Hard reservation for one order

Natural language: Fifty pieces of component X are reserved for Order 1 and must be unavailable to every generic component-X rule.

A flat key such as `reserved_for: order_1` is insufficient because consume selectors are partial: a generic selector containing only `type: component_x_each` would still match the extra key. Lossless reservation therefore requires a distinct item identity.

```yaml
inventory:
  - item:
      type: component_x_each
      location: plant_a_component_storage
    quantity: 950

  - item:
      type: component_x_reserved_order_1_each
      location: plant_a_component_storage
    quantity: 50
```

The route serving Order 1 explicitly consumes the reserved identity:

```yaml
rules:
  - id: assemble_order_1_with_reserved_component_x
    equipments:
      - function: assemble_product
    batch:
      minimum: 1
      maximum: 50
    consume:
      - item:
          type: component_x_reserved_order_1_each
          location: plant_a_component_storage
        quantity: 1
    produce:
      - item:
          type: product_for_order_1_each
          location: plant_a_finished_storage
        quantity: 1
    duration: 1h
```

Generic rules selecting `type: component_x_each` cannot consume the reserved quantity. This is finite and lossless, but reserving midway through planning requires the compiler to split inventory identities and generate the order-specific downstream rules.

#### Hard safety-stock floor

Natural language: Keep 100 kg of steel unavailable to ordinary production.

```yaml
inventory:
  - item:
      type: steel_kg
      location: plant_a_raw_storage
    quantity: 900

  - item:
      type: steel_safety_stock_kg
      location: plant_a_raw_storage
    quantity: 100
```

Ordinary production rules consume only `steel_kg`, so the 100 kg floor cannot be breached. If emergency release is allowed, define an explicit authorized conversion:

```yaml
rules:
  - id: release_steel_safety_stock
    batch:
      minimum: 1
      maximum: 100
    consume_per_batch:
      - item:
          type: safety_stock_release_authorization
        quantity: 1
    consume:
      - item:
          type: steel_safety_stock_kg
          location: plant_a_raw_storage
        quantity: 1
    produce:
      - item:
          type: steel_kg
          location: plant_a_raw_storage
        quantity: 1
    duration: 0m
```

The authorization item is supplied only when policy permits emergency use. Replenishing the floor is a demand for `steel_safety_stock_kg` or an explicit conversion back into that identity.

#### Expiry-aware residual inventory loss

Natural language: Expiring inventory left when the planning horizon completes contributes loss to the final objective. Earlier expiry produces a larger loss, but the optimizer may still consume a later-expiring lot when using the earlier lot would require excessive movement, delay a critical order, or create a larger loss elsewhere.

This is more general than mandatory FEFO. Consider:

```yaml
inventory:
  - id: chemical_a_nearby
    item:
      type: chemical_a_kg
      location: line_side_storage
      value: 2000
      price: 2600
    quantity: 100
    expires_at: 2026-08-20T00:00:00+08:00

  - id: chemical_a_early_remote
    item:
      type: chemical_a_kg
      location: remote_warehouse
      value: 2000
      price: 2600
    quantity: 100
    expires_at: 2026-07-25T00:00:00+08:00
```

Strict FEFO would always force the remote lot first. The loss model instead compares its avoided expiry loss with the movement time, transporter occupation, money consumption, and effects on other orders.

`value` and `price` are reserved integer fields on every compiled item:

- `value` is the virtual value of one item quantum to the company and is used when inventory is lost, destroyed, or expires;
- `price` is the virtual external acquisition or replacement cost of one item quantum, even when that item is not normally purchased.

`price` does not create inventory by itself. Actual procurement still needs a rule because money alone does not define lead time, supplier capacity, batch limits, or delivery location.

If a lot expires during the planning period, the quantity still remaining at its expiry incurs its full value:

```text
full expiry loss = remaining quantity at expiry * item value
```

The expired quantity becomes unusable from that time onward. Quantity consumed before expiry incurs no expiry loss.

If the lot expires after the planning horizon, its terminal remaining quantity incurs a fraction of its value. The fraction decreases as expiry moves farther into the future:

```text
future expiry loss
  = ceil(remaining quantity at horizon
       * item value
       * configured risk numerator
       / configured risk denominator)
```

This is a compiler-known integer objective calculation, not an arbitrary user formula. The risk fraction comes from a finite deterministic time-to-expiry table:

```yaml
expiry_loss_fraction:
  - expires_during_plan:
      numerator: 1
      denominator: 1
  - expires_within_after_plan: 7d
    numerator: 3
    denominator: 4
  - expires_within_after_plan: 30d
    numerator: 1
    denominator: 2
  - expires_later:
    numerator: 1
    denominator: 10
```

The compiler selects exactly one band and converts it into a fixed integer loss coefficient for each lot before solving. All divisions use ceiling; the solver receives no floating-point values.

Expiry still has a separate hard meaning: a lot must be consumed no later than `expires_at`. The residual-loss term influences which valid lot should be consumed before then; it does not make expired inventory usable after that instant.

Therefore:

- expiry eligibility is a hard inventory constraint;
- quantity expiring inside the horizon incurs full `value`;
- quantity expiring after the horizon incurs a decreasing fraction of `value`;
- `price` describes replacement economics but does not imply an automatic procurement path;
- earliest-expiry consumption is an emergent tradeoff, not a mandatory allocation sequence.

#### Hard case: age-triggered state transition

Natural language: A fresh adhesive remains usable for seven days, then automatically becomes a lower-strength adhesive that is still usable for another process.

`expires_after: 7d` can make the fresh item unusable, but it does not create the degraded item. An optional degradation rule could run too early, too late, or never.

The missing semantic is a compulsory transition at a time relative to lot creation:

```text
at produced_at + 7d:
  remaining fresh_adhesive_kg
    -> degraded_adhesive_kg
```

For existing inventory, the compiler can materialize a fixed future transition timestamp. For inventory produced by solver-selected executions, the transition time is itself relative to the chosen production time.

A finite candidate is an allowlisted relative state transition attached to a produced quantity. This is different from uncertainty: the transition time and output ratio are deterministic integers.

#### Alternate material

Natural language: Product P may use either resin A or qualified substitute resin B. The substitute is a separate complete transformation, not a conditional branch.

```yaml
rules:
  - id: mold_product_p_with_resin_a
    equipments:
      - function: mold_product_p
    batch:
      minimum: 1
      maximum: 100
    consume:
      - item:
          type: resin_a_kg
          location: plant_a_material_storage
        quantity: 2
    produce:
      - item:
          type: product_p_each
          location: plant_a_finished_storage
        quantity: 1
    duration: 1h

  - id: mold_product_p_with_resin_b
    equipments:
      - function: mold_product_p
    batch:
      minimum: 1
      maximum: 100
    consume:
      - item:
          type: resin_b_polymer_grade_1_kg
          location: plant_a_material_storage
        quantity: 2
      - item:
          type: money_cent
        quantity: 50
    produce:
      - item:
          type: product_p_each
          location: plant_a_finished_storage
        quantity: 1
    duration: 1h
```

The optimizer may use either rule whenever its inputs and equipment are available. No “use B only when A is short” condition is needed: inventory availability and the additional integer cost determine the tradeoff.

### 3) Movement and internal logistics

#### Capacity-constrained intra-plant movement

Natural language: Move up to 200 WIP boards from Workshop A to Workshop B. The move costs 5 money cents per board and occupies one suitable forklift for two hours.

```yaml
rules:
  - id: move_wip_board_workshop_a_to_b
    equipments:
      - function: move_workshop_a_to_b
    batch:
      minimum: 1
      maximum: 200
    consume:
      - item:
          type: wip_board_each
          location: workshop_a
        quantity: 1
      - item:
          type: money_cent
        quantity: 5
    produce:
      - item:
          type: wip_board_each
          location: workshop_b
        quantity: 1
    duration: 2h
```

#### Ignored or zero-time nearby movement

If two stations are operationally the same planning location, normalize both to one location and create no movement rule.

If their identities must remain visible, use an explicit zero-time transformation:

```yaml
rules:
  - id: move_part_x_line_1_station_1_to_2
    batch:
      minimum: 1
      maximum: 10000
    consume:
      - item:
          type: part_x_each
          location: line_1_station_1
        quantity: 1
    produce:
      - item:
          type: part_x_each
          location: line_1_station_2
        quantity: 1
    duration: 0m
```

Zero-time cycles must be rejected during validation because they can create infinitely many equivalent plans.

#### Dedicated round-trip transport

Natural language: A dedicated shuttle moves up to 2000 motors from Warehouse A to Warehouse B in ten hours and returns to Warehouse A in another two hours.

```yaml
rules:
  - id: shuttle_motors_warehouse_a_to_b
    equipments:
      - function: shuttle_warehouse_a_to_b_round_trip
    batch:
      minimum: 1
      maximum: 2000
    consume:
      - item:
          type: motor_each
          location: warehouse_a
        quantity: 1
    produce:
      - item:
          type: motor_each
          location: warehouse_b
        quantity: 1
    duration: 12h
```

The twelve-hour occupation includes the empty return, so the shuttle is stateless from the planner's perspective: every execution starts and ends ready at Warehouse A.

#### Reusable vehicle changes location

Natural language: A truck starts at Warehouse A, carries a variable quantity to Warehouse B, and remains at Warehouse B. Its next eligible trip depends on that new location.

Static equipment selectors and interval occupation are insufficient. They prevent simultaneous use of the same truck, but they do not change the truck's location after the execution. The planner could incorrectly schedule the same truck next on an unrelated route starting at Warehouse C.

The truck can instead be represented as a reusable state token:

```yaml
consume_per_batch:
  - item:
      type: truck_at_warehouse_a
    quantity: 1

consume:
  - item:
      type: motor_each
      location: warehouse_a
    quantity: 1

produce:
  - item:
      type: motor_each
      location: warehouse_b
    quantity: 1

produce_per_batch:
  - item:
      type: truck_at_warehouse_b
    quantity: 1
```

For cargo batch quantity `q`, the rule must consume and reproduce exactly one truck while moving `q` motors. Ordinary `produce` cannot express this because it would produce `q` trucks, so the language uses symmetric `produce_per_batch`.

`produce_per_batch` is accepted as the symmetric primitive. The complete rule is:

```yaml
rules:
  - id: truck_motors_warehouse_a_to_b
    batch:
      minimum: 1
      maximum: 2000
    consume_per_batch:
      - item:
          type: truck_at_warehouse_a
        quantity: 1
    consume:
      - item:
          type: motor_each
          location: warehouse_a
        quantity: 1
    produce:
      - item:
          type: motor_each
          location: warehouse_b
        quantity: 1
    produce_per_batch:
      - item:
          type: truck_at_warehouse_b
        quantity: 1
    duration: 10h
```

For selected cargo quantity `q`:

```text
1 truck_at_warehouse_a + q motor_each@warehouse_a
  -> 1 truck_at_warehouse_b + q motor_each@warehouse_b
```

The consumed truck token does not exist during the ten-hour execution, so it cannot be used concurrently. Its destination token appears only at completion, making the next trip location-correct without a separate equipment-state subsystem.

### 4) Core manufacturing transforms

#### Assembly

Natural language: One motherboard, one battery, and one screen are assembled into one phone in eight minutes.

```yaml
rules:
  - id: assemble_phone_v1
    equipments:
      - function: assemble_phone_v1
    batch:
      minimum: 1
      maximum: 1
    consume:
      - item:
          type: motherboard_v1_each
          location: phone_assembly_input
        quantity: 1
      - item:
          type: battery_v2_each
          location: phone_assembly_input
        quantity: 1
      - item:
          type: screen_v1_each
          location: phone_assembly_input
        quantity: 1
    produce:
      - item:
          type: phone_v1_each
          location: phone_assembly_output
        quantity: 1
    duration: 8m
```

Repeated phones are represented by repeated executions. The one-unit batch avoids silently treating an eight-minute-per-phone operation as an eight-minute variable-size batch.

#### Deterministic statistical yield

Natural language: CNC milling takes twelve minutes per raw block and historically produces 98% accepted components and 2% scrap. APS plans the deterministic integer ratio.

```yaml
rules:
  - id: mill_component_a
    equipments:
      - function: mill_component_a
    batch:
      minimum: 1
      maximum: 1
    consume:
      - item:
          type: raw_block_each
          location: cnc_input
        quantity: 100
    produce:
      - item:
          type: component_a_each
          location: cnc_output
        quantity: 98
      - item:
          type: scrap_metal_each
          location: cnc_scrap_output
        quantity: 2
    duration: 1200m
```

Input, output, and timing are scaled together:

```text
100 raw blocks
  -> 98 accepted components + 2 scrap
  in 100 * 12 minutes
```

No float or uncertain outcome enters the engine. Additional volume uses additional executions.

#### No-wait paint-to-cure handoff through relative expiry

Natural language: A painted part must enter curing immediately when painting finishes. Waiting even one minute invalidates the part.

Separate transformations correctly express material sequence:

```yaml
rules:
  - id: paint_part
    equipments:
      - function: paint_part
    batch:
      minimum: 1
      maximum: 1
    consume:
      - item:
          type: unpainted_part_each
          location: paint_input
        quantity: 1
    produce:
      - item:
          type: freshly_painted_part_each
          location: paint_output
        quantity: 1
        expires_after: 0m
    duration: 20m

  - id: cure_painted_part
    equipments:
      - function: cure_painted_part
    batch:
      minimum: 1
      maximum: 1
    consume:
      - item:
          type: freshly_painted_part_each
          location: paint_output
        quantity: 1
    produce:
      - item:
          type: cured_part_each
          location: cure_output
        quantity: 1
    duration: 40m
```

`expires_after` is an integer duration relative to the producing execution's completion:

```text
produced lot expires_at = producing execution end + expires_after
```

Consumption is valid when its start time is no later than the lot's `expires_at`. Therefore `expires_after: 0m` requires cure to start exactly when paint completes. A bounded wait uses the same primitive:

```yaml
expires_after: 15m
```

Existing inventory uses absolute `expires_at`; planned outputs use relative `expires_after`, which compiles to the same lot expiry field. Normal lot provenance already associates each produced quantity with its production time, so no separate no-wait primitive or special lineage system is required.

If the freshly painted part is not consumed by expiry, it becomes unusable and incurs the normal expiry loss based on its `value`.

#### Fixed-cycle heat-treatment batch

Natural language: One oven run heat-treats between 1 and 100 gear blanks in two hours.

```yaml
rules:
  - id: heat_treat_gear_blank
    equipments:
      - function: heat_treat_gear
    batch:
      minimum: 1
      maximum: 100
    consume:
      - item:
          type: gear_blank_each
          location: heat_treat_input
        quantity: 1
    produce:
      - item:
          type: heat_treated_gear_each
          location: heat_treat_output
        quantity: 1
    duration: 2h
```

The two-hour duration is fixed for every allowed batch quantity. This is the intended meaning of variable batch quantity with fixed-cycle duration.

#### Co-product and by-product

Natural language: One cutting execution converts 100 kg of sheet into 80 finished blanks, 15 kg reusable offcut, and 5 kg waste.

```yaml
rules:
  - id: cut_sheet_into_blanks
    equipments:
      - function: cut_sheet_blank
    batch:
      minimum: 1
      maximum: 1
    consume:
      - item:
          type: sheet_steel_kg
          location: cutting_input
        quantity: 100
    produce:
      - item:
          type: cut_blank_each
          location: cutting_output
        quantity: 80
      - item:
          type: reusable_offcut_kg
          location: offcut_storage
        quantity: 15
      - item:
          type: cutting_waste_kg
          location: waste_storage
        quantity: 5
    duration: 1h
```

Every deterministic output appears explicitly. Primary product, co-product, scrap, and waste have identical rule semantics.

#### Re-entrant and alternate routing

Re-entry is represented by distinct item states for each completed pass:

```text
wafer_unetched
  -> wafer_etched_pass_1
  -> wafer_cleaned_pass_1
  -> wafer_etched_pass_2
```

Each arrow is an ordinary finite rule. Alternative routes are separate complete rules producing the same downstream item. No path or loop primitive is required.

#### Transfer-batch overlap

Natural language: An upstream machine continuously produces 100 pieces over one hour. The downstream operation may start after the first 20 pieces finish while the upstream machine continues producing the remaining 80.

If every 20-piece segment is independently executable, use the ordinary rule:

```yaml
rules:
  - id: process_twenty_parts
    equipments:
      - function: process_part
    batch:
      minimum: 1
      maximum: 1
    consume:
      - item:
          type: raw_part_each
        quantity: 20
    produce:
      - item:
          type: processed_part_each
        quantity: 20
    duration: 12m
```

Five executions produce 20 parts every 12 minutes and allow downstream overlap.

If the five segments must form one uninterrupted machine campaign, use native equipment state plus WIP held inside that selected equipment.

The first stage can be:

```yaml
rules:
  - id: progressive_process_stage_1
    equipments:
      - bind: processor
        function: progressive_process
        state: ready
        state_after: stage_2
    batch:
      minimum: 1
      maximum: 1
    consume:
      - item:
          type: part_0_percent_each
        quantity: 100
    produce:
      - item:
          type: part_20_percent_each
          location: stage_1_output
        quantity: 20
      - item:
          type: part_20_percent_for_next_each
          held_by: processor
        quantity: 80
        expires_after: 0m
    duration: 12m
```

`bind: processor` is a rule-local name for the selected equipment instance. `held_by: processor` compiles to that instance's identity, so another identical machine cannot consume the internal WIP.

The next stage requires the same equipment and internal WIP:

```yaml
  - id: progressive_process_stage_2
    equipments:
      - bind: processor
        function: progressive_process
        state: stage_2
        state_after: stage_3
    batch:
      minimum: 1
      maximum: 1
    consume:
      - item:
          type: part_20_percent_for_next_each
          held_by: processor
        quantity: 80
    produce:
      - item:
          type: part_40_percent_each
          location: stage_2_output
        quantity: 20
      - item:
          type: part_40_percent_for_next_each
          held_by: processor
        quantity: 60
        expires_after: 0m
    duration: 12m
```

The zero relative expiry gives exactly two valid immediate choices:

1. continue with the next stage;
2. execute an explicit abort/cleanout rule that consumes the internal WIP, produces scrap, and returns the equipment to `ready`.

Simply allowing the WIP to expire records value loss but does not clean or reset the equipment, so discard must be an explicit rule.

#### Blocking flow through held WIP and equipment state

Natural language: Machine A finishes processing a part, but the part remains on Machine A until Machine B accepts it.

Machine A transitions from `processing` to `blocked_with_output` and produces the item with `held_by: machine_a`. Normal Machine A rules require `state: ready`, so it remains unavailable during the wait even though no active processing interval exists.

The handoff rule simultaneously:

- requires Machine A in `blocked_with_output`;
- requires Machine B in its receiving state;
- consumes the item held by Machine A;
- returns Machine A to `ready`;
- advances Machine B and the material.

Therefore blocking flow is also finite once equipment state and held WIP are accepted.

### 5) Resource/capability assignment

Equipment objects advertise finite functions. Rules select equipment by function, never by a discrete equipment id:

```yaml
equipment:
  - id: cnc_1
    functions:
      - mill_component_a
      - drill_component_a

  - id: cnc_2
    functions:
      - mill_component_a
```

`{ function: mill_component_a }` matches either machine. Every selected equipment instance participates in at most one active execution at a time.

#### Simultaneous machine, operator, and fixture

```yaml
rules:
  - id: laser_cut_housing
    equipments:
      - function: laser_cut_housing
      - function: operate_laser
      - function: hold_housing_fixture
    batch:
      minimum: 1
      maximum: 1
    consume:
      - item:
          type: housing_blank_each
          location: laser_input
        quantity: 1
    produce:
      - item:
          type: laser_cut_housing_each
          location: laser_output
        quantity: 1
    duration: 10m
```

All three selected equipment instances are occupied for the complete ten-minute interval.

#### Fixed crew size

Repeating one selector requires distinct matching equipment instances:

```yaml
equipments:
  - function: lift_heavy_assembly
  - function: lift_heavy_assembly
  - function: supervise_heavy_assembly
```

This requires two distinct lifters and one supervisor. The engine must reject satisfying repeated requirements with the same equipment instance.

#### Fixed production rate

Natural language: A machine produces exactly 20 pieces per hour. Reduce the rate to the smallest practical integer time quantum:

```yaml
rules:
  - id: machine_component_x
    equipments:
      - function: machine_component_x
    batch:
      minimum: 1
      maximum: 1
    consume:
      - item:
          type: component_x_blank_each
        quantity: 1
    produce:
      - item:
          type: component_x_each
        quantity: 1
    duration: 3m
```

Rational rates are scaled by increasing both item quantum and duration until all values are integers.

#### Equipment affinity

If one equipment/item combination has a different duration or cost, represent it as another explicit function and rule:

```yaml
rules:
  - id: mill_titanium_on_high_torque_cnc
    equipments:
      - function: mill_titanium_fast
    batch:
      minimum: 1
      maximum: 1
    consume:
      - item:
          type: titanium_blank_each
        quantity: 1
    produce:
      - item:
          type: titanium_component_each
        quantity: 1
    duration: 20m
```

Finite rule expansion replaces runtime affinity formulas.

#### Expansion-heavy case: fixed setup time plus quantity-linear run time

Natural language: One execution takes 30 minutes to set up, then 3 minutes for each selected item.

For batch quantity `q`, the required duration is:

```text
30m + 3m * q
```

A fixed `duration` cannot express this. Repeating `q` one-item executions incorrectly pays the 30-minute setup `q` times. One fixed-cycle variable batch incorrectly gives every quantity the same duration.

Because batch bounds are finite, this is losslessly representable by generating one fixed-duration rule for each permitted quantity:

```text
q=1 -> duration 33m
q=2 -> duration 36m
...
q=100 -> duration 330m
```

Integer `duration_per_batch` plus `duration_per_item` may be accepted as authoring/compiler sugar to avoid rule explosion, but it is not a semantic gap in the finite language.

### 6) Calendar and shift

Recurring calendars are expanded into finite availability intervals for the planning horizon:

```yaml
equipment_availability:
  - equipment: cnc_1
    intervals:
      - start: 2026-07-27T08:00:00+08:00
        end: 2026-07-27T17:00:00+08:00
      - start: 2026-07-28T08:00:00+08:00
        end: 2026-07-28T17:00:00+08:00
```

The engine receives timestamps, not an open-ended recurrence language. Planned downtime subtracts intervals before solving:

```yaml
equipment_unavailability:
  - equipment: cnc_1
    start: 2026-08-05T09:00:00+08:00
    end: 2026-08-05T13:00:00+08:00
```

#### Start-only windows

A rule or required execution may restrict its start to finite windows:

```yaml
start_windows:
  - start: 2026-07-27T08:00:00+08:00
    end: 2026-07-27T10:00:00+08:00
  - start: 2026-07-28T08:00:00+08:00
    end: 2026-07-28T10:00:00+08:00
```

The execution may finish outside a start window if its selected equipment remains available.

#### Hard case: overtime cost depends on scheduled overlap

Natural language: Machine time from 08:00–17:00 has no premium. Time from 17:00–21:00 costs 100 money cents per occupied minute.

A rule's ordinary `consume` cost is independent of when the solver schedules it. The required premium is:

```text
integer minutes of execution overlapping overtime windows
  * 100 money_cent
```

This cannot be represented by one fixed rule cost when an execution may overlap regular and overtime periods. Finite options:

1. add integer cost coefficients to availability intervals and charge overlap;
2. require executions to fit wholly inside one regular/overtime window, then use separate rule alternatives;
3. split every operation at the regular/overtime boundary.

Option 2 is sufficient for non-preemptive operations that fit one window. General overlap requires a compiler-known time-window objective term.

#### Hard case: resumable work across unavailable intervals

Natural language: An eight-hour operation may run four hours before shift end, pause overnight, and resume for four hours next morning without repeating setup.

The current execution is one continuous occupied interval. Splitting it into two rules loses remaining-progress state and may repeat fixed setup consumption.

Lossless modeling requires either:

1. a resumable execution whose duration counts only available working ticks;
2. explicit integer progress-state items produced at each interruption;
3. pre-expanded fixed work segments and precedence constraints.

This is distinct from an elapsed-time process, such as curing, which continues while equipment calendars are closed.

### 7) Setup and changeover

Reusable per-execution state tokens model sequence-dependent equipment state without mutable equipment fields.

#### Production preserves equipment state

```yaml
rules:
  - id: press_family_a
    batch:
      minimum: 1
      maximum: 100
    consume_per_batch:
      - item:
          type: press_ready_family_a
        quantity: 1
    consume:
      - item:
          type: family_a_blank_each
        quantity: 1
    produce:
      - item:
          type: family_a_part_each
        quantity: 1
    produce_per_batch:
      - item:
          type: press_ready_family_a
        quantity: 1
    duration: 1h
```

The press token is unavailable during execution and returns in the same state afterward.

#### Product-family changeover

```yaml
  - id: change_press_family_a_to_b
    batch:
      minimum: 1
      maximum: 1
    consume_per_batch:
      - item:
          type: press_ready_family_a
        quantity: 1
      - item:
          type: cleaning_agent_each
        quantity: 1
    produce_per_batch:
      - item:
          type: press_ready_family_b
        quantity: 1
    duration: 40m
```

Every allowed directed state transition is an explicit rule. Different reverse duration or cleaning consumption requires another rule.

#### Warmup and bounded hot state

```yaml
  - id: warm_oven
    batch:
      minimum: 1
      maximum: 1
    consume_per_batch:
      - item:
          type: oven_cold
        quantity: 1
    produce_per_batch:
      - item:
          type: oven_hot
        quantity: 1
        expires_after: 2h
    duration: 30m

  - id: cool_oven
    batch:
      minimum: 1
      maximum: 1
    consume_per_batch:
      - item:
          type: oven_hot
        quantity: 1
    produce_per_batch:
      - item:
          type: oven_cold
        quantity: 1
    duration: 0m
```

The oven must use or convert its hot token no later than two hours after warmup. A hard terminal requirement preserving one oven-state token prevents the optimizer from discarding the reusable oven and paying only a soft value loss.

#### Sequence-dependent setup matrix

A matrix is finite rule expansion:

```text
tool_t1 -> tool_t2: 25m
tool_t2 -> tool_t1: 15m
tool_t1 -> tool_t3: 40m
```

becomes three directed token-conversion rules. Missing transitions are impossible.

#### Expansion-heavy equipment identity

State tokens are lossless when equipment with the same token type is interchangeable. If individual machines have different calendars, maintenance counters, or transition histories, the token must include machine identity. That requires per-machine generated rules or an accepted selector-copy mechanism; a generic state token must not be paired with the wrong physical machine.

Per-machine token and rule generation is finite and lossless. A bounded equipment-state transition may be useful compiler sugar, but no new semantic primitive is required.

### 8) Quality, rework, scrap

#### Inspection gate

Shipping rules consume only released item identities. Inspection converts awaiting-inspection phones into deterministic released and failed quantities:

```yaml
rules:
  - id: inspect_phone_v1
    equipments:
      - function: inspect_phone_v1
    batch:
      minimum: 1
      maximum: 10
    consume:
      - item:
          type: phone_v1_awaiting_inspection_each
          location: phone_inspection_queue
        quantity: 100
    produce:
      - item:
          type: phone_v1_released_each
          location: released_finished_storage
        quantity: 98
      - item:
          type: phone_v1_failed_each
          location: failed_finished_storage
        quantity: 2
    duration: 2h
```

#### Hold and release

An external quality decision is represented by a finite authorization item:

```yaml
  - id: release_held_phone_lot
    batch:
      minimum: 1
      maximum: 10000
    consume_per_batch:
      - item:
          type: release_authorization_phone_lot_1042
        quantity: 1
    consume:
      - item:
          type: phone_v1_held_each
          lot: lot_1042
        quantity: 1
    produce:
      - item:
          type: phone_v1_released_each
          lot: lot_1042
        quantity: 1
    duration: 0m
```

The authorization item is imported only after the external quality system makes the decision. APS does not choose an uncertain release outcome.

#### Deterministic rework

```yaml
  - id: rework_failed_phone_v1
    equipments:
      - function: rework_phone_v1
    batch:
      minimum: 1
      maximum: 10
    consume:
      - item:
          type: phone_v1_failed_each
          location: failed_finished_storage
        quantity: 100
    produce:
      - item:
          type: phone_v1_released_each
          location: released_finished_storage
        quantity: 90
      - item:
          type: electronic_scrap_each
          location: waste_storage
        quantity: 10
    duration: 20h
```

#### Scrap disposal

```yaml
  - id: dispose_electronic_scrap
    equipments:
      - function: dispose_electronic_scrap
    batch:
      minimum: 1
      maximum: 1000
    consume_per_batch:
      - item:
          type: money_cent
        quantity: 5000
    consume:
      - item:
          type: electronic_scrap_each
          location: waste_storage
        quantity: 1
      - item:
          type: money_cent
        quantity: 20
    duration: 1h
```

#### Regulatory segregation through explicit state

Equipment contamination class can use the same reusable state-token pattern as setup. A dairy production rule requires and returns `mixer_dairy_state`; switching to allergen-free production requires an explicit cleaning rule that converts it to `mixer_allergen_free_state`.

#### Hard case: traceability-key propagation

Natural language: Supplier lot, heat number, serial range, and purchase-order identity must survive inbound, machining, inspection, rework, and outsourcing.

Consume selectors are partial and produced item objects are explicit. Therefore this input:

```yaml
item:
  type: steel_kg
  supplier_lot: lot_1042
  heat: heat_77
```

does not automatically transfer `supplier_lot` or `heat` to the output.

Finite options:

1. generate one complete rule for every known traceability-key combination;
2. add bounded `copy_from_consume` with an explicit finite key allowlist;
3. represent every traceable lot as a distinct item type and duplicate downstream rules.

Option 1 is lossless for known horizon data but can create a product of rules across several keys. Option 2 is the smallest runtime primitive:

```yaml
produce:
  - item:
      type: machined_component_each
    copy_from_consume:
      source: raw_material
      keys:
        - supplier_lot
        - heat
```

It is not general interpolation: only listed keys are copied unchanged from one named consumed quantity. Rules involving several input lots still need an explicit policy for which source contributes each output key or how parent-lot references are recorded.

### 9) Outsourcing and subcontracting

Outsourcing is ordinary movement plus an external equipment function.

```yaml
rules:
  - id: ship_raw_part_to_anodizer_a
    equipments:
      - function: transport_plant_a_to_anodizer_a
    batch:
      minimum: 1
      maximum: 2000
    consume:
      - item:
          type: raw_part_each
          location: plant_a_outbound
        quantity: 1
    produce:
      - item:
          type: raw_part_each
          location: anodizer_a_inbound
        quantity: 1
    duration: 1d

  - id: anodize_part_at_vendor_a
    equipments:
      - function: vendor_a_anodize
    batch:
      minimum: 100
      maximum: 2000
    consume:
      - item:
          type: raw_part_each
          location: anodizer_a_inbound
        quantity: 1
      - item:
          type: money_cent
        quantity: 300
    produce:
      - item:
          type: anodized_part_each
          location: anodizer_a_outbound
        quantity: 1
    duration: 3d

  - id: return_anodized_part_from_vendor_a
    equipments:
      - function: transport_anodizer_a_to_plant_a
    batch:
      minimum: 1
      maximum: 2000
    consume:
      - item:
          type: anodized_part_each
          location: anodizer_a_outbound
        quantity: 1
    produce:
      - item:
          type: anodized_part_each
          location: plant_a_inbound_queue
        quantity: 1
    duration: 1d
```

Vendor B is another complete set of rules with its own price, capacity, batch limits, locations, and durations. The objective chooses among feasible routes.

Supplier-controlled timing variation is not represented as uncertainty. Confirmed vendor receipts become future inventory; changed promises are imported and trigger replanning.

### 10) Maintenance and reliability

#### Calendar-scheduled maintenance

A confirmed maintenance interval is a required state-token transformation:

```yaml
rules:
  - id: maintain_cnc_1
    equipments:
      - function: maintain_cnc
    batch:
      minimum: 1
      maximum: 1
    consume_per_batch:
      - item:
          type: cnc_1_ready
        quantity: 1
      - item:
          type: maintenance_kit_cnc_each
        quantity: 1
      - item:
          type: money_cent
        quantity: 20000
    produce_per_batch:
      - item:
          type: cnc_1_ready
        quantity: 1
    duration: 3h

execution_requirements:
  - id: cnc_1_pm_2026_08_05
    rule: maintain_cnc_1
    batch_quantity: 1
    start_window:
      earliest: 2026-08-05T08:00:00+08:00
      latest: 2026-08-05T12:00:00+08:00
```

#### Repair after an observed failure

Failure is imported as current state, never predicted as an uncertain event:

```yaml
inventory:
  - item:
      type: cnc_1_failed
    quantity: 1

rules:
  - id: repair_cnc_1
    equipments:
      - function: repair_cnc
    batch:
      minimum: 1
      maximum: 1
    consume_per_batch:
      - item:
          type: cnc_1_failed
        quantity: 1
      - item:
          type: cnc_spare_part_kit_each
        quantity: 1
      - item:
          type: money_cent
        quantity: 50000
    produce_per_batch:
      - item:
          type: cnc_1_ready
        quantity: 1
    duration: 4h
```

#### Hard case: usage-triggered maintenance counter

Natural language: CNC 1 must receive maintenance before accumulating more than 120 runtime hours, and maintenance resets its counter to zero.

Each production execution must:

```text
increase cnc_1 runtime by its occupied processing time
```

The counter belongs to one physical CNC, must survive across many different production rules, has a hard upper bound, and resets during maintenance.

Ordinary item quantities can approximate remaining runtime tokens, but early maintenance creates a reset problem: producing another 7200 minute tokens while unused tokens remain would accumulate more than the allowed capacity. Encoding the remaining counter in item identity requires one state and transition rule for every possible integer value.

Finite options:

1. add a bounded integer field on a reusable equipment-state token with constant increment/decrement and reset operations;
2. add resource-local cumulative counters as a compiler-known primitive;
3. expand every reachable counter value into explicit item identities and rules.

Option 3 is theoretically finite but can multiply every production rule by thousands of counter states.

#### Hard case: condition-dependent performance

Natural language: Equipment condition decreases with runtime; below integer threshold 70 it runs slower, and maintenance restores condition to 100.

Finite condition bands can use separate state-token identities and explicit production rules, but continuous decrement again requires a bounded counter transition on every execution. Time-based degradation while idle additionally requires scheduled state changes. This is the same cumulative-state primitive as usage-triggered maintenance, not an affinity formula.

### 11) Order and fulfillment

The planning session needs finite goal records in addition to transformation rules:

```yaml
goals:
  - id: order_1
    item:
      type: phone_v1_released_each
      location: shipping
    quantity: 1000
    release_at: 2026-07-27T08:00:00+08:00
    due_at: 2026-07-30T17:00:00+08:00
    unfulfilled_loss_per_item: 100000
    late_loss_per_item_per_minute: 100
```

All quantities and objective coefficients are integers. Existing inventory or any valid rule route may satisfy the goal.

#### Strict make-to-order release

If `release_at` means production for this order may not begin early, generate an order authorization item available at release and an order-specific first transformation:

```yaml
inventory:
  - item:
      type: order_1_production_authorization
    quantity: 1
    available_at: 2026-07-27T08:00:00+08:00
```

Make-to-stock production may still occur earlier and later satisfy the order. This distinction cannot be inferred from the due date alone.

#### Partial shipment milestones

Represent milestones as separate cumulative goal quantities:

```yaml
goals:
  - id: order_2_first_delivery
    item:
      type: phone_v1_released_each
      location: customer_2
    quantity: 200
    due_at: 2026-07-29T17:00:00+08:00

  - id: order_2_final_delivery
    item:
      type: phone_v1_released_each
      location: customer_2
    quantity: 1000
    due_at: 2026-08-02T17:00:00+08:00
```

The second quantity is cumulative; the compiler converts it to an additional 800 units after accounting for the first milestone.

#### Priority

Priority classes compile into integer lateness and unfulfilled-loss coefficients. They do not alter rule feasibility.

#### Hard case: allocation fairness

Natural language: When supply is insufficient, no customer segment should receive a disproportionately low fill rate.

This compares fulfilled fractions across several goals:

```text
fulfilled_quantity / requested_quantity
```

Independent linear shortage penalties do not guarantee max-min fairness; a high-value segment may consume everything. Exact max-min fairness needs rational cross-goal constraints or staged optimization:

1. maximize the minimum integer-scaled fill fraction;
2. fix that optimum;
3. optimize ordinary cost/service objectives.

This is a global goal-allocation primitive, not a transformation rule.

### 12) Replanning and lock control

#### Completed and started execution

Completed executions are realized history. Their consumed inventory is gone, their outputs are current inventory, and they no longer appear as decisions.

A started execution becomes:

- fixed equipment unavailability until its confirmed end;
- fixed future output inventory at that end;
- imported realized consumption.

No selectable rule execution is needed for the already-started work.

#### Freeze fence

Prior approved executions starting inside the freeze fence become required executions with fixed rule, quantity, start, and selected reusable state/equipment bindings. Executions outside the fence remain movable.

#### Stability objective

For a prior execution retaining the same stable id:

```text
absolute new-start minus old-start
  * integer movement-loss coefficient

+ integer equipment-change loss when selected equipment differs
```

These are compiler-known integer objective terms.

#### Hard case: stability across split, merge, and rebatching

A prior 100-unit execution may become two 50-unit executions, or two prior executions may merge. There is no obvious one-to-one execution id for calculating movement loss.

Finite options:

1. forbid split/merge for prior executions and preserve stable ids;
2. match old and new quantities using a minimum-cost flow before or inside optimization;
3. measure stability at order/item/time-bucket level rather than execution identity.

Option 1 is simple but can block necessary replanning. Option 2 is lossless but adds a cross-plan matching problem. Option 3 changes the meaning of stability.

#### Delta limit

A hard maximum number of changed execution ids is a finite cardinality constraint after identity matching. It inherits the same split/merge ambiguity.

### 13) Composite objective policies

Every objective term is an integer loss in one common virtual-value scale:

- consumed `money_cent`;
- unfulfilled goal loss;
- lateness loss;
- expired or at-risk inventory `value`;
- overtime-window loss;
- changeover consumption;
- stability loss;
- optional emissions, waste, or risk items with integer objective weights.

#### Weighted profile

```yaml
objective:
  mode: weighted
  terms:
    - term: unfulfilled_goal_loss
      weight: 1000
    - term: lateness_loss
      weight: 100
    - term: money_consumed
      weight: 1
    - term: expiry_loss
      weight: 1
    - term: stability_loss
      weight: 1
```

The compiler multiplies integer coefficients and checks overflow before solving.

#### Lexicographic profile

When one concern must never be traded for another, solve in ordered stages:

```yaml
objective:
  mode: lexicographic
  stages:
    - minimize: unfulfilled_goal_loss
    - minimize: lateness_loss
    - minimize: expiry_loss
    - minimize: money_consumed
    - minimize: stability_loss
```

Each stage fixes the prior optimum before solving the next. This avoids inventing enormous weights to approximate strict priority.

Throughput is represented by fulfilled goal quantity or avoided unfulfilled loss, not by rewarding arbitrary inventory production. This prevents value-generating cycles from appearing profitable merely because produced items have high `value`.

On-time delivery count, maximum lateness, and similar non-additive KPIs require compiler-known auxiliary integer/Boolean variables, but remain finite objective primitives rather than user formulas.

## Collected hard cases

The following cases cannot be represented losslessly by only:

```text
fixed rule duration
+ proportional/per-execution consume and produce
+ equipment selectors
+ absolute/relative expiry
+ finite goals and integer linear loss terms
```

| Hard case | Why current transformations are insufficient | Smallest candidate primitive |
|---|---|---|
| Overtime/window overlap cost | Cost depends on where an execution interval overlaps priced calendar windows. | Integer cost per occupied tick on finite availability intervals. |
| Resumable execution | Work may pause across unavailable periods without losing progress or repeating setup. | Working-tick duration or explicit progress-state segments. |
| Traceability propagation | Explicit outputs do not retain selected keys from one or several consumed lots. | Allowlisted `copy_from_consume`, plus explicit multi-parent lineage policy. |
| Resource-local cumulative counters | Runtime/cycle/condition state increments across many rules and resets during maintenance. | Bounded integer fields on reusable state tokens with add/subtract/reset. |
| Allocation fairness | Max-min fill rate compares rational fulfillment across several goals. | Integer-scaled global fairness constraint with staged optimization. |
| Replan stability after split/merge | Old and new executions lack a one-to-one identity after rebatching. | Quantity-aware minimum-cost matching or a different stability metric. |
| Indivisible dynamic lot/order | A dynamically sized lot or approved requisition may need all-or-none routing without permitting optimizer splitting. | Group identity with aggregate quantity and indivisibility. |
| Aggregate commercial grouping | Price/lead-time policy may depend on the sum of several executions in one day or contract period. | Finite execution group with aggregate quantity and tier selection. |
| Age-triggered state transition | Relative expiry can invalidate an item but cannot automatically convert fresh inventory into an aged/degraded item after elapsed shelf time. | Relative timed state-transition event tied to lot creation. |

Cases deliberately **not** classified as hard:

- multiple suppliers or routes: separate complete rules;
- normal order splitting: multiple executions;
- no-wait/bounded-wait handoff: relative `expires_after`;
- reusable vehicle location: `consume_per_batch` + `produce_per_batch` state token;
- deterministic yield: integer transformation vector;
- finite timed material events: independent transfer batches or no-wait equipment-state stage expansion;
- blocking flow: equipment state plus WIP bound to the selected equipment;
- fixed setup plus quantity-linear duration: exhaustive fixed-duration rule generation;
- sequence-dependent setup: directed reusable state-token rules;
- stateful equipment identity: per-instance state-token and rule generation;
- weekly supplier quota: dated consumable quota items;
- FEFO: expiry-derived residual value loss rather than mandatory ordering;
- repair after observed failure: imported failed-state token plus repair rule.

## What remains outside this catalog (for now)

- Fine-grained stochastic execution and uncertainty propagation.
- Full multi-echelon network planning across many plants/distribution nodes.
- Detailed financial cashflow constraints (beyond objective accounting items).
- Detailed real-time dispatch policy logic that belongs to MES/dispatch systems.
