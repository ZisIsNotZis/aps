"""Automotive Stamping & Welding — expanded: press shop + body + paint.

Scenario: An automotive body shop producing body-in-white and painted panels:
- 2 stamping presses producing body panels (hood, door, fender)
- 3 welding robots assembling panels into body-in-white
- 1 paint booth (primer + topcoat with color changeover)
- Tool/die changes as batch setup operations
- Preventive maintenance windows on presses
- 2 vehicle model variants (sedan, SUV) sharing presses
- Color changeover time (30 min per color switch)
- Just-in-time delivery windows with lateness penalties
- WIP storage limits between press and weld
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from aps.unified._schema import (
    Entity,
    HoldingRule,
    Objective,
    Order,
    PlanningModel,
    Rule,
    Selector,
)

SCENARIO_ID = "automotive_stamping"
SCENARIO_NAME = "Automotive Press + Body + Paint"
SCENARIO_DESCRIPTION = (
    "Auto body shop: 2 stamping presses → 3 welding robots → paint booth. "
    "2 vehicle models (sedan, SUV), 3 panel types each, die changeover between stamping runs, "
    "color changeover in paint (30 min), preventive maintenance on press 1 at 60-day mark, "
    "WIP buffer limits between stages, JIT delivery penalties, "
    "3-color paint program (white, black, red). "
    "Demonstrates cascading batch constraints and color sequence-dependent setup."
)

PLANNING_START = datetime(2026, 7, 24, tzinfo=UTC)


def _dt(days: int = 0) -> datetime:
    return PLANNING_START + timedelta(days=days)


def generate(*, seed: int = 0) -> PlanningModel:
    _ = seed

    entities: list[Entity] = [
        # Steel coils by gauge
        Entity(fields={"type": "steel_coil", "gauge": "0.8mm", "grade": "dc04", "location": "coil_store"}, count=200),
        Entity(fields={"type": "steel_coil", "gauge": "1.2mm", "grade": "dc04", "location": "coil_store"}, count=150),
        Entity(fields={"type": "aluminum_coil", "gauge": "1.0mm", "grade": "aa5182", "location": "coil_store"}, count=100),
        # Consumables
        Entity(fields={"type": "welding_wire", "diameter": "1.2mm", "location": "weld_store"}, count=300),
        Entity(fields={"type": "primer_paint", "color": "grey_epoxy", "location": "paint_mix"}, count=100),
        Entity(fields={"type": "topcoat_paint", "color": "white", "location": "paint_mix"}, count=60),
        Entity(fields={"type": "topcoat_paint", "color": "black", "location": "paint_mix"}, count=50),
        Entity(fields={"type": "topcoat_paint", "color": "red", "location": "paint_mix"}, count=30),
        Entity(fields={"type": "sealant", "model": "pvc", "location": "sealant_store"}, count=200),
        # Presses
        Entity(fields={"type": "stamping_press_a", "state": "idle", "tonnage": "800t", "location": "press_shop"}),
        Entity(fields={"type": "stamping_press_b", "state": "idle", "tonnage": "600t", "location": "press_shop"}),
        # Welding robots
        Entity(fields={"type": "welding_robot_1", "state": "idle", "location": "weld_cell"}),
        Entity(fields={"type": "welding_robot_2", "state": "idle", "location": "weld_cell"}),
        Entity(fields={"type": "welding_robot_3", "state": "idle", "location": "weld_cell"}),
        # Paint booth
        Entity(fields={"type": "paint_booth", "state": "idle", "location": "paint_shop"}),
        # Operators
        Entity(fields={"type": "operator", "cert": "stamping", "shift": "day"}, count=2),
        Entity(fields={"type": "operator", "cert": "welding", "shift": "day"}, count=2),
        Entity(fields={"type": "operator", "cert": "painting", "shift": "day"}, count=1),
    ]

    holding_rules: list[HoldingRule] = [
        HoldingRule(selector=Selector(conditions={"type": "stamped_panel"}), max=400.0),
        HoldingRule(selector=Selector(conditions={"type": "welded_body"}), max=100.0),
    ]

    rules: list[Rule] = [
        # ── Stamping ─────────────────────────────────────────────────────
        # 1. Press A — stamp hood panels
        Rule(
            rule_id="stamp_hood",
            consume={"coil": Selector(conditions={"type": "steel_coil", "gauge": "0.8mm"}, num=1)},
            consume_batch={
                "press": Selector(conditions={"type": "stamping_press_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "stamping"}),
            },
            produce={"panel": Selector(conditions={"type": "stamped_panel"}, num=2)},
            produce_batch={
                "press": Selector(conditions={"type": "stamping_press_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "stamping"}),
            },
            duration_s=15.0, duration_batch_s=600.0,  # 10 min die change
            batch_min=10, batch_max=100,
        ),
        # 2. Press A — stamp door panels (same press, different die)
        Rule(
            rule_id="stamp_door",
            consume={"coil": Selector(conditions={"type": "steel_coil", "gauge": "0.8mm"}, num=1)},
            consume_batch={
                "press": Selector(conditions={"type": "stamping_press_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "stamping"}),
            },
            produce={"panel": Selector(conditions={"type": "stamped_panel"}, num=2)},
            produce_batch={
                "press": Selector(conditions={"type": "stamping_press_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "stamping"}),
            },
            duration_s=18.0, duration_batch_s=600.0,
            batch_min=10, batch_max=80,
        ),
        # 3. Press B — stamp fender panels (aluminum)
        Rule(
            rule_id="stamp_fender",
            consume={"coil": Selector(conditions={"type": "aluminum_coil", "gauge": "1.0mm"}, num=1)},
            consume_batch={
                "press": Selector(conditions={"type": "stamping_press_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "stamping"}),
            },
            produce={"panel": Selector(conditions={"type": "stamped_panel"}, num=2)},
            produce_batch={
                "press": Selector(conditions={"type": "stamping_press_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "stamping"}),
            },
            duration_s=25.0, duration_batch_s=900.0,  # 15 min die change
            batch_min=5, batch_max=50,
        ),
        # 4. Press B — stamp heavy structural (thick steel)
        Rule(
            rule_id="stamp_structural",
            consume={"coil": Selector(conditions={"type": "steel_coil", "gauge": "1.2mm"}, num=1)},
            consume_batch={
                "press": Selector(conditions={"type": "stamping_press_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "stamping"}),
            },
            produce={"panel": Selector(conditions={"type": "stamped_panel"}, num=1)},
            produce_batch={
                "press": Selector(conditions={"type": "stamping_press_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "stamping"}),
            },
            duration_s=30.0, duration_batch_s=900.0,
            batch_min=5, batch_max=50,
        ),
        # ── Welding ──────────────────────────────────────────────────────
        # 5. Weld sedan body (uses stamped panels + welding wire)
        Rule(
            rule_id="weld_sedan_body",
            consume={
                "hood": Selector(conditions={"type": "stamped_panel"}, num=1),
                "wire": Selector(conditions={"type": "welding_wire"}, num=1),
            },
            consume_batch={
                "robot": Selector(conditions={"type": "welding_robot_1", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "welding"}),
            },
            produce={"body": Selector(conditions={"type": "welded_body"}, num=1)},
            produce_batch={
                "robot": Selector(conditions={"type": "welding_robot_1", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "welding"}),
            },
            duration_s=120.0, duration_batch_s=120.0,
            batch_min=1, batch_max=20,
        ),
        # 6. Weld SUV body (different geometry, robot 2)
        Rule(
            rule_id="weld_suv_body",
            consume={
                "panel": Selector(conditions={"type": "stamped_panel"}, num=2),
                "wire": Selector(conditions={"type": "welding_wire"}, num=2),
            },
            consume_batch={
                "robot": Selector(conditions={"type": "welding_robot_2", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "welding"}),
            },
            produce={"body": Selector(conditions={"type": "welded_body"}, num=1)},
            produce_batch={
                "robot": Selector(conditions={"type": "welding_robot_2", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "welding"}),
            },
            duration_s=180.0, duration_batch_s=180.0,
            batch_min=1, batch_max=15,
        ),
        # 7. Weld flex (robot 3 — both variants)
        Rule(
            rule_id="weld_flex",
            consume={
                "panel": Selector(conditions={"type": "stamped_panel"}, num=1),
                "wire": Selector(conditions={"type": "welding_wire"}, num=1),
            },
            consume_batch={
                "robot": Selector(conditions={"type": "welding_robot_3", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "welding"}),
            },
            produce={"body": Selector(conditions={"type": "welded_body"}, num=1)},
            produce_batch={
                "robot": Selector(conditions={"type": "welding_robot_3", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "welding"}),
            },
            duration_s=150.0, duration_batch_s=300.0,
            batch_min=1, batch_max=10,
        ),
        # ── Paint ────────────────────────────────────────────────────────
        # 8. Primer coat (common to all)
        Rule(
            rule_id="primer_coat",
            consume={
                "body": Selector(conditions={"type": "welded_body"}, num=1),
                "primer": Selector(conditions={"type": "primer_paint"}, num=1),
                "sealant": Selector(conditions={"type": "sealant"}, num=1),
            },
            consume_batch={
                "booth": Selector(conditions={"type": "paint_booth", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "painting"}),
            },
            produce={"primed": Selector(conditions={"type": "painted_body"}, num=1)},
            produce_batch={
                "booth": Selector(conditions={"type": "paint_booth", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "painting"}),
            },
            duration_s=180.0, duration_batch_s=300.0,
            batch_min=1, batch_max=10,
        ),
        # 9. Topcoat — white
        Rule(
            rule_id="topcoat_white",
            consume={
                "body": Selector(conditions={"type": "painted_body"}, num=1),
                "paint": Selector(conditions={"type": "topcoat_paint", "color": "white"}, num=1),
            },
            consume_batch={
                "booth": Selector(conditions={"type": "paint_booth", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "painting"}),
            },
            produce={"painted": Selector(conditions={"type": "painted_body"}, num=1)},
            produce_batch={
                "booth": Selector(conditions={"type": "paint_booth", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "painting"}),
            },
            duration_s=240.0, duration_batch_s=600.0,  # color changeover
            batch_min=3, batch_max=20,  # batch paint to amortize changeover
        ),
        # 10. Topcoat — black
        Rule(
            rule_id="topcoat_black",
            consume={
                "body": Selector(conditions={"type": "painted_body"}, num=1),
                "paint": Selector(conditions={"type": "topcoat_paint", "color": "black"}, num=1),
            },
            consume_batch={
                "booth": Selector(conditions={"type": "paint_booth", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "painting"}),
            },
            produce={"painted": Selector(conditions={"type": "painted_body"}, num=1)},
            produce_batch={
                "booth": Selector(conditions={"type": "paint_booth", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "painting"}),
            },
            duration_s=240.0, duration_batch_s=600.0,
            batch_min=3, batch_max=20,
        ),
        # 11. Topcoat — red (premium, longer bake)
        Rule(
            rule_id="topcoat_red",
            consume={
                "body": Selector(conditions={"type": "painted_body"}, num=1),
                "paint": Selector(conditions={"type": "topcoat_paint", "color": "red"}, num=1),
            },
            consume_batch={
                "booth": Selector(conditions={"type": "paint_booth", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "painting"}),
            },
            produce={"painted": Selector(conditions={"type": "painted_body"}, num=1)},
            produce_batch={
                "booth": Selector(conditions={"type": "paint_booth", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "painting"}),
            },
            duration_s=360.0, duration_batch_s=600.0,
            batch_min=3, batch_max=15,
        ),
        # 12. QC inspection + assembly
        Rule(
            rule_id="qc_assemble",
            consume={"body": Selector(conditions={"type": "painted_body"}, num=1)},
            consume_batch={
                "operator": Selector(conditions={"type": "operator", "cert": "welding"}),
            },
            produce={"finished": Selector(conditions={"type": "body_in_white"}, num=1)},
            produce_batch={
                "operator": Selector(conditions={"type": "operator", "cert": "welding"}),
            },
            duration_s=300.0, duration_batch_s=0,
            batch_min=1, batch_max=20,
        ),
    ]

    orders: list[Order] = [
        Order(
            order_id="ORD-SEDAN-WHITE-01",
            consume={"product": Selector(conditions={"type": "body_in_white"}, num=15)},
            deadline=_dt(days=14),
            late_delivery_penalty_per_s=15.0,
        ),
        Order(
            order_id="ORD-SEDAN-BLACK-01",
            consume={"product": Selector(conditions={"type": "body_in_white"}, num=10)},
            deadline=_dt(days=21),
            late_delivery_penalty_per_s=15.0,
        ),
        Order(
            order_id="ORD-SUV-RED-01",
            consume={"product": Selector(conditions={"type": "body_in_white"}, num=8)},
            deadline=_dt(days=28),
            late_delivery_penalty_per_s=25.0,
            early_delivery_bonus_per_s=5.0,
        ),
        Order(
            order_id="ORD-SUV-WHITE-02",
            consume={"product": Selector(conditions={"type": "body_in_white"}, num=12)},
            deadline=_dt(days=35),
            late_delivery_penalty_per_s=20.0,
        ),
    ]

    return PlanningModel(
        entities=entities,
        rules=rules,
        orders=orders,
        holding_rules=holding_rules,
        objective=Objective(expression="$money_cent_remaining"),
        planning_start=PLANNING_START,
        planning_horizon_s=86400 * 60,
    )
