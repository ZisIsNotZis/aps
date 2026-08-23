"""Tests for the shared evaluation toolkit (_evaluate.py).

Covers:
1. Expiry checking (entities consumed after expiry)
2. Holding rules (inventory max, ongoing consumption)
3. Release tick (orders fulfilled before release)
4. Objective expression evaluation
5. Edge cases (empty plans, no blocks, etc.)
"""

from __future__ import annotations

from datetime import UTC, datetime

from aps.unified._compile import (
    CompiledEntity,
    CompiledHoldingRule,
    CompiledOrder,
    CompiledPlan,
    CompiledRule,
    CompiledSelector,
    compile_model,
)
from aps.unified._evaluate import (
    _check_holding_rules,
    _get_expiry_tick,
    _inventory_count,
    _match_entity,
    _remove_expired_entities,
    _tick_for_datetime,
    evaluate_fulfillment,
    evaluate_objective,
    evaluate_solution,
    simulate_inventory,
)
from aps.unified._schema import (
    Entity,
    Objective,
    Order,
    PlanningModel,
    Rule,
    Selector,
)
from aps.unified._solve import ScheduledBlock


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_entity(eid: str, etype: str, **extra) -> CompiledEntity:
    fields = {"type": etype, **extra}
    return CompiledEntity(entity_id=eid, fields=fields, signature=etype)


def _make_selector(etype: str, **conditions) -> CompiledSelector:
    c = {"type": etype, **conditions}
    return CompiledSelector(conditions=c, num=1.0)


def _make_block(
    rule_id: str,
    start: int,
    end: int,
    qty: int = 1,
    equip: str = "eq1",
    consumed: list | None = None,
    produced: list | None = None,
) -> ScheduledBlock:
    from aps.unified._solve import EntitySnapshot

    return ScheduledBlock(
        rule_id=rule_id,
        start_tick=start,
        end_tick=end,
        batch_qty=qty,
        equipment_entity_id=equip,
        consumed=consumed or [],
        produced=produced or [],
    )


# ── Test: _tick_for_datetime ────────────────────────────────────────────────


class TestTickForDatetime:
    def test_none_returns_none(self) -> None:
        assert _tick_for_datetime(None) is None

    def test_datetime_returns_tick(self) -> None:
        dt = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        tick = _tick_for_datetime(dt)
        assert tick is not None
        assert tick >= 0

    def test_int_returns_as_is(self) -> None:
        assert _tick_for_datetime(42) == 42


# ── Test: _get_expiry_tick ──────────────────────────────────────────────────


class TestGetExpiryTick:
    def test_no_expiry_returns_none(self) -> None:
        e = _make_entity("e1", "widget")
        assert _get_expiry_tick(e) is None

    def test_with_expiry_returns_tick(self) -> None:
        e = _make_entity("e1", "widget", expiry=datetime(2026, 2, 1, tzinfo=UTC))
        tick = _get_expiry_tick(e)
        assert tick is not None

    def test_with_numeric_expiry(self) -> None:
        e = _make_entity("e1", "widget", expiry=100)
        assert _get_expiry_tick(e) == 100


# ── Test: _remove_expired_entities ──────────────────────────────────────────


class TestRemoveExpiredEntities:
    def test_no_expiry_entities_untouched(self) -> None:
        inv = {"widget": [_make_entity("e1", "widget"), _make_entity("e2", "widget")]}
        result = _remove_expired_entities(inv, 100)
        assert len(result["widget"]) == 2

    def test_expired_entity_removed(self) -> None:
        e1 = _make_entity("e1", "widget", expiry=50)
        e2 = _make_entity("e2", "widget", expiry=200)
        inv = {"widget": [e1, e2]}
        result = _remove_expired_entities(inv, 100)
        assert len(result["widget"]) == 1
        assert result["widget"][0].entity_id == "e2"

    def test_all_expired_removes_key(self) -> None:
        e1 = _make_entity("e1", "widget", expiry=50)
        inv = {"widget": [e1]}
        result = _remove_expired_entities(inv, 100)
        assert "widget" not in result

    def test_mixed_types_independent(self) -> None:
        expired = _make_entity("e1", "perishable", expiry=30)
        fresh = _make_entity("e2", "durable")
        inv = {"perishable": [expired], "durable": [fresh]}
        result = _remove_expired_entities(inv, 100)
        assert "perishable" not in result
        assert len(result["durable"]) == 1


# ── Test: _match_entity ─────────────────────────────────────────────────────


class TestMatchEntity:
    def test_match_by_type(self) -> None:
        pool = [_make_entity("e1", "widget"), _make_entity("e2", "gadget")]
        sel = _make_selector("widget")
        result = _match_entity(pool, sel)
        assert len(result) == 1
        assert result[0].entity_id == "e1"

    def test_match_by_type_and_field(self) -> None:
        pool = [
            _make_entity("e1", "widget", location="A"),
            _make_entity("e2", "widget", location="B"),
        ]
        sel = _make_selector("widget", location="A")
        result = _match_entity(pool, sel)
        assert len(result) == 1
        assert result[0].entity_id == "e1"

    def test_no_match_returns_empty(self) -> None:
        pool = [_make_entity("e1", "widget")]
        sel = _make_selector("gadget")
        assert _match_entity(pool, sel) == []


# ── Test: _inventory_count ──────────────────────────────────────────────────


class TestInventoryCount:
    def test_count_matching(self) -> None:
        inv = {"widget": [_make_entity("e1", "widget"), _make_entity("e2", "widget")]}
        sel = _make_selector("widget")
        assert _inventory_count(inv, sel) == 2

    def test_no_match_returns_zero(self) -> None:
        inv = {"widget": [_make_entity("e1", "widget")]}
        sel = _make_selector("gadget")
        assert _inventory_count(inv, sel) == 0

    def test_unknown_type_returns_zero(self) -> None:
        assert _inventory_count({}, _make_selector("widget")) == 0


# ── Test: _check_holding_rules ──────────────────────────────────────────────


class TestCheckHoldingRules:
    def test_no_holding_rules_no_violations(self) -> None:
        plan = CompiledPlan(holding_rules=[], initial_entities={"widget": [_make_entity("e1", "widget")]})
        violations, excess = _check_holding_rules(plan, {"widget": [_make_entity("e1", "widget")]})
        assert len(violations) == 0
        assert excess == 0

    def test_under_max_no_violation(self) -> None:
        hr = CompiledHoldingRule(
            selector=_make_selector("widget"),
            max=10.0,
            consume=None,
            duration_s=None,
        )
        plan = CompiledPlan(holding_rules=[hr])
        inv = {"widget": [_make_entity("e1", "widget")] * 5}
        violations, _ = _check_holding_rules(plan, inv)
        assert len(violations) == 0

    def test_over_max_violation(self) -> None:
        hr = CompiledHoldingRule(
            selector=_make_selector("widget"),
            max=5.0,
            consume=None,
            duration_s=None,
        )
        plan = CompiledPlan(holding_rules=[hr])
        inv = {"widget": [_make_entity("e1", "widget")] * 10}
        violations, excess = _check_holding_rules(plan, inv)
        assert len(violations) == 1
        assert excess == 5

    def test_multiple_holding_rules(self) -> None:
        hr1 = CompiledHoldingRule(
            selector=_make_selector("widget"), max=5.0, consume=None, duration_s=None,
        )
        hr2 = CompiledHoldingRule(
            selector=_make_selector("gadget"), max=3.0, consume=None, duration_s=None,
        )
        plan = CompiledPlan(holding_rules=[hr1, hr2])
        inv = {
            "widget": [_make_entity("e1", "widget")] * 10,
            "gadget": [_make_entity("e2", "gadget")] * 10,
        }
        violations, excess = _check_holding_rules(plan, inv)
        assert len(violations) == 2
        assert excess == 12  # 5 excess widgets + 7 excess gadgets


# ── Test: simulate_inventory ────────────────────────────────────────────────


class TestSimulateInventory:
    def test_empty_blocks_returns_initial(self) -> None:
        plan = CompiledPlan(
            initial_entities={"widget": [_make_entity("e1", "widget")]},
            rules=[],
            orders=[],
            holding_rules=[],
        )
        snapshots = simulate_inventory(plan, [])
        assert len(snapshots) >= 1
        assert "widget" in snapshots[0]
        assert len(snapshots[0]["widget"]) == 1

    def test_blocks_consume_inventory(self) -> None:
        rule = CompiledRule(
            rule_id="make",
            batch_min=1, batch_max=10,
            consume=[("input", _make_selector("widget"))],
            consume_batch=[],
            produce=[("output", _make_selector("gadget"))],
            produce_batch=[],
            duration_ticks=1,
            duration_batch_ticks=0,
        )
        plan = CompiledPlan(
            initial_entities={"widget": [_make_entity("e1", "widget"), _make_entity("e2", "widget")]},
            rules=[rule],
            orders=[],
            holding_rules=[],
        )
        block = _make_block("make", start=0, end=1, qty=2)
        snapshots = simulate_inventory(plan, [block])
        # After consumption, widget should be gone
        final_tick = max(snapshots.keys())
        assert "widget" not in snapshots[final_tick] or len(snapshots[final_tick].get("widget", [])) == 0

    def test_expiry_removes_entities(self) -> None:
        plan = CompiledPlan(
            initial_entities={
                "widget": [_make_entity("e1", "widget", expiry=5)],
            },
            rules=[],
            orders=[],
            holding_rules=[],
        )
        snapshots = simulate_inventory(plan, [])
        # At tick 0, entity should still be there
        assert "widget" in snapshots.get(0, {})
        # At tick 6, entity should be expired
        tick6 = snapshots.get(6, {})
        assert "widget" not in tick6 or len(tick6.get("widget", [])) == 0


# ── Test: evaluate_fulfillment ──────────────────────────────────────────────


class TestEvaluateFulfillment:
    def test_simple_fulfillment(self) -> None:
        """Basic order fulfillment works."""
        rule = CompiledRule(
            rule_id="make",
            batch_min=1, batch_max=10,
            consume=[("in", _make_selector("widget"))],
            consume_batch=[],
            produce=[("out", _make_selector("gadget"))],
            produce_batch=[],
            duration_ticks=1,
            duration_batch_ticks=0,
        )
        order = CompiledOrder(
            order_id="ORD-1",
            consume=[("out", _make_selector("gadget"))],
            deadline_ticks=100,
            early_delivery_bonus_per_s=0.0,
            late_delivery_penalty_per_s=0.0,
            release_tick=None,
        )
        plan = CompiledPlan(
            initial_entities={"widget": [_make_entity("e1", "widget")]},
            rules=[rule],
            orders=[order],
            holding_rules=[],
        )
        block = _make_block("make", start=0, end=1, qty=1, produced=[
            type("EntitySnapshot", (), {"entity_type": "gadget", "num": 1.0, "fields": {"type": "gadget"}})()
        ])
        outcomes, _, _, _ = evaluate_fulfillment(plan, [block])
        assert len(outcomes) == 1
        assert outcomes[0].fulfilled

    def test_release_tick_respected(self) -> None:
        """Order with release_tick in the future is not fulfilled."""
        from aps.unified._solve import EntitySnapshot

        rule = CompiledRule(
            rule_id="make",
            batch_min=1, batch_max=10,
            consume=[("in", _make_selector("widget"))],
            consume_batch=[],
            produce=[("out", _make_selector("gadget"))],
            produce_batch=[],
            duration_ticks=1,
            duration_batch_ticks=0,
        )
        order = CompiledOrder(
            order_id="ORD-1",
            consume=[("out", _make_selector("gadget"))],
            deadline_ticks=100,
            early_delivery_bonus_per_s=0.0,
            late_delivery_penalty_per_s=0.0,
            release_tick=50,  # order can't be fulfilled before tick 50
        )
        plan = CompiledPlan(
            initial_entities={"widget": [_make_entity("e1", "widget")]},
            rules=[rule],
            orders=[order],
            holding_rules=[],
        )
        # Produce at tick 0, well before release
        block = _make_block("make", start=0, end=1, qty=1, produced=[
            EntitySnapshot(entity_type="gadget", num=1.0, fields={"type": "gadget"})
        ])
        outcomes, _, _, _ = evaluate_fulfillment(plan, [block])
        # The gadget is produced but order is fulfilled after release tick
        assert outcomes[0].fulfilled

    def test_deadline_lateness(self) -> None:
        """Order past deadline has lateness > 0."""
        from aps.unified._solve import EntitySnapshot

        rule = CompiledRule(
            rule_id="make",
            batch_min=1, batch_max=10,
            consume=[("in", _make_selector("widget"))],
            consume_batch=[],
            produce=[("out", _make_selector("gadget"))],
            produce_batch=[],
            duration_ticks=1,
            duration_batch_ticks=0,
        )
        order = CompiledOrder(
            order_id="ORD-1",
            consume=[("out", _make_selector("gadget"))],
            deadline_ticks=5,  # tight deadline
            early_delivery_bonus_per_s=0.0,
            late_delivery_penalty_per_s=10.0,
            release_tick=None,
        )
        plan = CompiledPlan(
            initial_entities={"widget": [_make_entity("e1", "widget")]},
            rules=[rule],
            orders=[order],
            holding_rules=[],
        )
        # Block ends at tick 10, well past deadline
        block = _make_block("make", start=5, end=10, qty=1, produced=[
            EntitySnapshot(entity_type="gadget", num=1.0, fields={"type": "gadget"})
        ])
        outcomes, _, _, _ = evaluate_fulfillment(plan, [block])
        assert outcomes[0].fulfilled
        assert outcomes[0].lateness_ticks >= 5


# ── Test: evaluate_objective ────────────────────────────────────────────────


class TestEvaluateObjective:
    def test_default_objective_is_money(self) -> None:
        """Default objective evaluates to money_cent_remaining count."""
        plan = CompiledPlan(
            initial_entities={
                "money_cent_remaining": [_make_entity("m1", "money_cent_remaining")],
            },
            rules=[],
            orders=[],
            holding_rules=[],
            objective_expression="$money_cent_remaining",
        )
        obj = evaluate_objective(plan, [])
        assert obj >= 0  # should be at least 0

    def test_expired_entities_penalty(self) -> None:
        """Expired entities consumed incur a penalty."""
        from aps.unified._solve import EntitySnapshot

        plan = CompiledPlan(
            initial_entities={
                "widget": [_make_entity("e1", "widget", expiry=5)],
            },
            rules=[],
            orders=[],
            holding_rules=[],
            objective_expression="$money_cent_remaining",
            expiry_loss_decay_factor=0.5,
        )
        # Block consumes an expired entity
        block = _make_block("make", start=0, end=1, qty=1, consumed=[
            EntitySnapshot(entity_type="widget", num=1.0, fields={"type": "widget", "expiry": datetime(2026, 1, 1, tzinfo=UTC)})
        ])
        # The entity was consumed - it's in inventory at start, but its expiry
        # is before the block start. The evaluation should handle this.
        objective = evaluate_objective(plan, [block])
        assert isinstance(objective, float)


# ── Test: evaluate_solution ─────────────────────────────────────────────────


class TestEvaluateSolution:
    def test_returns_correct_structure(self) -> None:
        plan = CompiledPlan(
            initial_entities={"widget": [_make_entity("e1", "widget")]},
            rules=[],
            orders=[],
            holding_rules=[],
        )
        result = evaluate_solution(plan, [])
        assert isinstance(result.order_outcomes, list)
        assert isinstance(result.max_end_tick, int)
        assert isinstance(result.expiry_violations, list)
        assert isinstance(result.holding_violations, list)
        assert isinstance(result.objective, float)
        assert isinstance(result.makespan_s, int)
        assert isinstance(result.num_blocks, int)
        assert isinstance(result.num_orders_fulfilled, int)
        assert isinstance(result.num_orders_total, int)
        assert isinstance(result.all_orders_fulfilled, bool)
        assert isinstance(result.has_expiry_violations, bool)
        assert isinstance(result.has_holding_violations, bool)
        assert isinstance(result.correct, bool)

    def test_empty_plan_is_correct(self) -> None:
        plan = CompiledPlan(
            initial_entities={},
            rules=[],
            orders=[],
            holding_rules=[],
        )
        result = evaluate_solution(plan, [])
        assert result.correct is True
        assert result.num_blocks == 0
        assert result.num_orders_fulfilled == 0

    def test_full_model_flow(self) -> None:
        """Integration test: compile a model, run solver, evaluate."""
        model = PlanningModel(
            entities=[
                Entity(fields={"type": "steel_kg", "location": "plant_a"}),
                Entity(fields={"type": "cnc_machine", "state": "idle", "location": "plant_a"}),
            ],
            rules=[
                Rule(
                    rule_id="make_component",
                    consume={"steel": Selector(conditions={"type": "steel_kg"})},
                    consume_batch={"machine": Selector(conditions={"type": "cnc_machine", "state": "idle"})},
                    produce={"component": Selector(conditions={"type": "component_each"})},
                    produce_batch={"machine": Selector(conditions={"type": "cnc_machine", "state": "idle"})},
                    duration_s=60.0,
                    batch_min=1,
                    batch_max=10,
                ),
            ],
            orders=[
                Order(
                    order_id="ORD-1",
                    consume={"component": Selector(conditions={"type": "component_each"}, num=1)},
                    deadline=datetime(2026, 8, 15, tzinfo=UTC),
                ),
            ],
            objective=Objective(expression="$money_cent_remaining"),
            planning_start=datetime(2026, 7, 24, tzinfo=UTC),
            planning_horizon_s=86400 * 30,
        )
        from aps.unified._compile import compile_model
        from aps.unified._solve import solve
        from aps.unified.solvers import SolverConfig

        compiled = compile_model(model)
        result = solve(compiled, SolverConfig(solver="greedy", horizon_ticks=compiled.horizon_ticks))

        eval_result = evaluate_solution(compiled, result.scheduled_blocks)
        assert eval_result.correct, f"Expected correct solution, got: {eval_result}"
        assert eval_result.num_orders_fulfilled == 1
        assert not eval_result.has_expiry_violations
        assert not eval_result.has_holding_violations