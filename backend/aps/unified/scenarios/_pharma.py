"""Pharmaceutical manufacturing — campaign-based batch production with expiry.

Scenario: A drug product manufacturing facility producing finished dosage forms:
- API + excipient blending → granulation → tablet compression → coating → packaging
- API and intermediate materials have strict expiry dates (shelf life)
- Campaign-based scheduling: once a line is set up, run full campaign
- Cleaning/changeover required between different products
- Holding rules for WIP storage costs and max inventory limits
- Dual sourcing: two tablet presses, two coating pans
- QC release hold after coating before packaging
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

SCENARIO_ID = "pharma_manufacturing"
SCENARIO_NAME = "Pharmaceutical Batch Manufacturing"
SCENARIO_DESCRIPTION = (
    "Drug product facility with 10 rules: API/excipient mixing → granulation "
    "→ tablet compression → coating → blister packaging. 2 drug variants, "
    "API expiry (90-day shelf life), cleaning campaigns between products, "
    "campaign setup times, QC release holds, WIP holding costs. "
    "Dual equipment lines for compression and coating."
)

PLANNING_START = datetime(2026, 7, 24, tzinfo=UTC)


def _dt(days: int = 0, hours: int = 0) -> datetime:
    return PLANNING_START + timedelta(days=days, hours=hours)


def generate(*, seed: int = 0) -> PlanningModel:
    _ = seed

    # ── Raw materials ───────────────────────────────────────────────────
    # API powders with expiry dates (90-day shelf life from planning start)
    api_expiry = _dt(days=90)
    entities: list[Entity] = [
        Entity(fields={"type": "api_powder_a", "expiry": api_expiry, "location": "cold_room"}, count=500),
        Entity(fields={"type": "api_powder_b", "expiry": api_expiry, "location": "cold_room"}, count=500),
        Entity(fields={"type": "excipient_binder", "location": "dry_store"}, count=2000),
        Entity(fields={"type": "excipient_filler", "location": "dry_store"}, count=3000),
        Entity(fields={"type": "coating_polymer", "location": "dry_store"}, count=1000),
        Entity(fields={"type": "blister_foil", "location": "packaging_store"}, count=500),
    ]

    # ── Equipment ───────────────────────────────────────────────────────
    entities += [
        Entity(fields={"type": "blender", "state": "idle", "location": "granulation_suite"}),
        Entity(fields={"type": "granulator", "state": "idle", "location": "granulation_suite"}),
        Entity(fields={"type": "drying_oven", "state": "idle", "location": "granulation_suite"}),
        Entity(fields={"type": "tablet_press_a", "state": "idle", "location": "compression_bay"}),
        Entity(fields={"type": "tablet_press_b", "state": "idle", "location": "compression_bay"}),
        Entity(fields={"type": "coater_a", "state": "idle", "location": "coating_bay"}),
        Entity(fields={"type": "coater_b", "state": "idle", "location": "coating_bay"}),
        Entity(fields={"type": "qc_station", "state": "idle", "location": "qc_lab"}),
        Entity(fields={"type": "packaging_line", "state": "idle", "location": "packaging_hall"}),
        Entity(fields={"type": "operator", "name": "technician_1", "cert": "granulation", "shift": "day"}),
        Entity(fields={"type": "operator", "name": "technician_2", "cert": "compression", "shift": "day"}),
        Entity(fields={"type": "operator", "name": "technician_3", "cert": "coating", "shift": "day"}),
        Entity(fields={"type": "operator", "name": "technician_4", "cert": "packaging", "shift": "day"}),
    ]

    # ── Holding rules ───────────────────────────────────────────────────
    # WIP storage costs: blending/granulation WIP costs 0.5/s per kg
    # Max WIP in granulation suite: 200 units
    holding_rules: list[HoldingRule] = [
        HoldingRule(
            selector=Selector(conditions={"type": "granulated_blend"}),
            max=200.0,
        ),
        HoldingRule(
            selector=Selector(conditions={"type": "compressed_core"}),
            max=500.0,
        ),
        HoldingRule(
            selector=Selector(conditions={"type": "coated_tablet"}),
            max=500.0,
        ),
    ]

    # ── Rules ───────────────────────────────────────────────────────────
    # 1. Blend API + excipient
    rules: list[Rule] = [
        Rule(
            rule_id="blend_api",
            consume={
                "api": Selector(conditions={"type": "api_powder_a"}, num=1),
                "binder": Selector(conditions={"type": "excipient_binder"}, num=2),
                "filler": Selector(conditions={"type": "excipient_filler"}, num=3),
            },
            consume_batch={
                "blender": Selector(conditions={"type": "blender", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "granulation"}),
            },
            produce={"blend": Selector(conditions={"type": "granulated_blend"}, num=5)},
            produce_batch={
                "blender": Selector(conditions={"type": "blender", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "granulation"}),
            },
            duration_s=120.0,
            duration_batch_s=300.0,  # setup/scavenge
            batch_min=10,
            batch_max=50,
        ),
        # 2. Blend API variant B
        Rule(
            rule_id="blend_api_b",
            consume={
                "api": Selector(conditions={"type": "api_powder_b"}, num=1),
                "binder": Selector(conditions={"type": "excipient_binder"}, num=2),
                "filler": Selector(conditions={"type": "excipient_filler"}, num=3),
            },
            consume_batch={
                "blender": Selector(conditions={"type": "blender", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "granulation"}),
            },
            produce={"blend": Selector(conditions={"type": "granulated_blend"}, num=5)},
            produce_batch={
                "blender": Selector(conditions={"type": "blender", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "granulation"}),
            },
            duration_s=120.0,
            duration_batch_s=600.0,  # longer cleaning changeover between APIs
            batch_min=10,
            batch_max=50,
        ),
        # 3. Granulate blend
        Rule(
            rule_id="granulate",
            consume={"blend": Selector(conditions={"type": "granulated_blend"}, num=1)},
            consume_batch={
                "granulator": Selector(conditions={"type": "granulator", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "granulation"}),
            },
            produce={"granules": Selector(conditions={"type": "granulated_blend"}, num=1)},
            produce_batch={
                "granulator": Selector(conditions={"type": "granulator", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "granulation"}),
            },
            duration_s=180.0,
            duration_batch_s=120.0,
            batch_min=10,
            batch_max=50,
        ),
        # 4. Dry granules
        Rule(
            rule_id="dry_granules",
            consume={"wet": Selector(conditions={"type": "granulated_blend"}, num=1)},
            consume_batch={
                "oven": Selector(conditions={"type": "drying_oven", "state": "idle"}),
            },
            produce={"dry": Selector(conditions={"type": "granulated_blend"}, num=1)},
            produce_batch={
                "oven": Selector(conditions={"type": "drying_oven", "state": "idle"}),
            },
            duration_s=300.0,
            duration_batch_s=60.0,
            batch_min=10,
            batch_max=50,
        ),
        # 5. Compress tablets on press A
        Rule(
            rule_id="compress_a",
            consume={"granules": Selector(conditions={"type": "granulated_blend"}, num=1)},
            consume_batch={
                "press": Selector(conditions={"type": "tablet_press_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "compression"}),
            },
            produce={"core": Selector(conditions={"type": "compressed_core"}, num=10)},
            produce_batch={
                "press": Selector(conditions={"type": "tablet_press_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "compression"}),
            },
            duration_s=30.0,
            duration_batch_s=600.0,  # tooling changeover
            batch_min=20,
            batch_max=100,
        ),
        # 6. Compress tablets on press B
        Rule(
            rule_id="compress_b",
            consume={"granules": Selector(conditions={"type": "granulated_blend"}, num=1)},
            consume_batch={
                "press": Selector(conditions={"type": "tablet_press_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "compression"}),
            },
            produce={"core": Selector(conditions={"type": "compressed_core"}, num=10)},
            produce_batch={
                "press": Selector(conditions={"type": "tablet_press_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "compression"}),
            },
            duration_s=30.0,
            duration_batch_s=600.0,
            batch_min=20,
            batch_max=100,
        ),
        # 7. Film-coat on coater A
        Rule(
            rule_id="coat_a",
            consume={
                "core": Selector(conditions={"type": "compressed_core"}, num=10),
                "polymer": Selector(conditions={"type": "coating_polymer"}, num=1),
            },
            consume_batch={
                "coater": Selector(conditions={"type": "coater_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "coating"}),
            },
            produce={"coated": Selector(conditions={"type": "coated_tablet"}, num=10)},
            produce_batch={
                "coater": Selector(conditions={"type": "coater_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "coating"}),
            },
            duration_s=60.0,
            duration_batch_s=900.0,  # cleaning between campaigns
            batch_min=20,
            batch_max=80,
        ),
        # 8. Film-coat on coater B
        Rule(
            rule_id="coat_b",
            consume={
                "core": Selector(conditions={"type": "compressed_core"}, num=10),
                "polymer": Selector(conditions={"type": "coating_polymer"}, num=1),
            },
            consume_batch={
                "coater": Selector(conditions={"type": "coater_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "coating"}),
            },
            produce={"coated": Selector(conditions={"type": "coated_tablet"}, num=10)},
            produce_batch={
                "coater": Selector(conditions={"type": "coater_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "coating"}),
            },
            duration_s=60.0,
            duration_batch_s=900.0,
            batch_min=20,
            batch_max=80,
        ),
        # 9. QC release
        Rule(
            rule_id="qc_release",
            consume={"sample": Selector(conditions={"type": "coated_tablet"}, num=1)},
            consume_batch={
                "qc": Selector(conditions={"type": "qc_station", "state": "idle"}),
            },
            produce={"released": Selector(conditions={"type": "coated_tablet"}, num=1)},
            produce_batch={
                "qc": Selector(conditions={"type": "qc_station", "state": "idle"}),
            },
            duration_s=60.0,
            duration_batch_s=3600.0,  # 1 hour QC hold
            batch_min=20,
            batch_max=100,
        ),
        # 10. Blister packaging
        Rule(
            rule_id="blister_pack",
            consume={
                "tablets": Selector(conditions={"type": "coated_tablet"}, num=10),
                "foil": Selector(conditions={"type": "blister_foil"}, num=1),
            },
            consume_batch={
                "line": Selector(conditions={"type": "packaging_line", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "packaging"}),
            },
            produce={"pack": Selector(conditions={"type": "blister_pack"}, num=1)},
            produce_batch={
                "line": Selector(conditions={"type": "packaging_line", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "packaging"}),
            },
            duration_s=15.0,
            duration_batch_s=300.0,
            batch_min=10,
            batch_max=100,
        ),
    ]

    # ── Orders ──────────────────────────────────────────────────────────
    orders: list[Order] = [
        Order(
            order_id="ORD-DRUG-A-01",
            consume={"product": Selector(conditions={"type": "blister_pack"}, num=200)},
            deadline=_dt(days=25),
            late_delivery_penalty_per_s=10.0,
        ),
        Order(
            order_id="ORD-DRUG-A-02",
            consume={"product": Selector(conditions={"type": "blister_pack"}, num=300)},
            deadline=_dt(days=40),
            late_delivery_penalty_per_s=10.0,
        ),
        Order(
            order_id="ORD-DRUG-B-01",
            consume={"product": Selector(conditions={"type": "blister_pack"}, num=150)},
            deadline=_dt(days=30),
            late_delivery_penalty_per_s=15.0,
            early_delivery_bonus_per_s=2.0,
        ),
    ]

    return PlanningModel(
        entities=entities,
        rules=rules,
        orders=orders,
        holding_rules=holding_rules,
        objective=Objective(expression="$money_cent_remaining", expiry_loss_decay_factor=0.3),
        planning_start=PLANNING_START,
        planning_horizon_s=86400 * 60,
    )
