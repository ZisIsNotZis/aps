"""Electronics SMT Assembly — expanded: SMT + final assembly with kitting.

Scenario: A surface-mount technology (SMT) PCB assembly + final product assembly:
- Solder paste → pick-and-place → reflow → AOI inspection (SMT line)
- Wave solder through-hole components (mixed technology)
- Conformal coating (moisture protection)
- Final assembly: enclosure + wiring + testing
- Kitting: sub-components arrive as kits from warehouse
- Component expiry (solder paste shelf life = 24h once opened)
- 2 SMT lines (high-speed and flexible), 1 wave solder line
- 2 product variants (controller, sensor module) with shared and unique components
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

SCENARIO_ID = "electronics_smt"
SCENARIO_NAME = "Electronics SMT + Assembly"
SCENARIO_DESCRIPTION = (
    "Expanded SMT + final assembly: 11 rules across paste → place → reflow → AOI → wave solder → "
    "coat → final assembly+test. 2 SMT lines, 2 product variants (controller, sensor), "
    "component kitting, solder paste expiry (24h shelf life), conformal coating, "
    "WIP holding costs, dual-source assembly benches."
)

PLANNING_START = datetime(2026, 7, 24, tzinfo=UTC)
SOLDER_PASTE_EXPIRY = PLANNING_START + timedelta(hours=24)


def _dt(days: int = 0) -> datetime:
    return PLANNING_START + timedelta(days=days)


def generate(*, seed: int = 0) -> PlanningModel:
    _ = seed

    entities: list[Entity] = [
        # Raw materials
        Entity(fields={"type": "pcb_board", "size": "100x80mm", "layers": "4", "location": "wip_store"}, count=2000),
        Entity(fields={"type": "pcb_board", "size": "120x100mm", "layers": "6", "location": "wip_store"}, count=2000),
        Entity(fields={"type": "solder_paste", "grade": "sac305", "expiry": SOLDER_PASTE_EXPIRY, "location": "fridge"}, count=2000),
        Entity(fields={"type": "silicon_chip", "part": "mcu_32bit", "location": "esd_store"}, count=2000),
        Entity(fields={"type": "silicon_chip", "part": "sensor_dsp", "location": "esd_store"}, count=1000),
        Entity(fields={"type": "capacitor", "value": "100nF", "package": "0603", "location": "reel_store"}, count=5000),
        Entity(fields={"type": "capacitor", "value": "10uF", "package": "0805", "location": "reel_store"}, count=3000),
        Entity(fields={"type": "resistor", "value": "1k", "package": "0603", "location": "reel_store"}, count=5000),
        Entity(fields={"type": "connector", "model": "usb_c", "location": "mechanical_store"}, count=2000),
        Entity(fields={"type": "connector", "model": "rj45", "location": "mechanical_store"}, count=2000),
        Entity(fields={"type": "enclosure", "model": "abs_black", "location": "mechanical_store"}, count=1000),
        Entity(fields={"type": "enclosure", "model": "abs_grey", "location": "mechanical_store"}, count=1000),
        Entity(fields={"type": "wire_harness", "length": "300mm", "location": "mechanical_store"}, count=2000),
        Entity(fields={"type": "coating_material", "model": "acrylic", "location": "chemical_store"}, count=5000),
        # Equipment
        Entity(fields={"type": "solder_printer_1", "state": "idle", "speed": "high"}),
        Entity(fields={"type": "solder_printer_2", "state": "idle", "speed": "flex"}),
        Entity(fields={"type": "pick_and_place_1", "state": "idle", "speed": "high", "capacity": "30k_cph"}),
        Entity(fields={"type": "pick_and_place_2", "state": "idle", "speed": "flex", "capacity": "15k_cph"}),
        Entity(fields={"type": "reflow_oven_1", "state": "idle", "zone_count": "10"}),
        Entity(fields={"type": "reflow_oven_2", "state": "idle", "zone_count": "8"}),
        Entity(fields={"type": "aoi_machine", "state": "idle", "model": "optical"}),
        Entity(fields={"type": "wave_solder", "state": "idle", "model": "selective"}, count=2),
        Entity(fields={"type": "coating_robot", "state": "idle", "model": "selective"}, count=2),
        Entity(fields={"type": "assembly_bench_1", "state": "idle", "location": "final_assem"}),
        Entity(fields={"type": "assembly_bench_2", "state": "idle", "location": "final_assem"}),
        Entity(fields={"type": "test_station", "state": "idle", "model": "functional"}, count=3),
        Entity(fields={"type": "operator", "cert": "smt", "shift": "day"}, count=2),
        Entity(fields={"type": "operator", "cert": "assembly", "shift": "day"}, count=2),
        Entity(fields={"type": "operator", "cert": "test", "shift": "day"}, count=3),
    ]

    holding_rules: list[HoldingRule] = [
        HoldingRule(selector=Selector(conditions={"type": "populated_pcb"}), max=300.0),
        HoldingRule(selector=Selector(conditions={"type": "tested_module"}), max=200.0),
    ]

    rules: list[Rule] = [
        # 1. Solder paste print — line 1 (high speed)
        Rule(
            rule_id="print_paste_1",
            consume={
                "pcb": Selector(conditions={"type": "pcb_board", "size": "100x80mm"}, num=1),
                "paste": Selector(conditions={"type": "solder_paste"}, num=1),
            },
            consume_batch={
                "printer": Selector(conditions={"type": "solder_printer_1", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            produce={"printed": Selector(conditions={"type": "paste_applied_pcb"}, num=1)},
            produce_batch={
                "printer": Selector(conditions={"type": "solder_printer_1", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            duration_s=30.0, duration_batch_s=120.0,
            batch_min=5, batch_max=30,
        ),
        # 2. Solder paste print — line 2 (flex)
        Rule(
            rule_id="print_paste_2",
            consume={
                "pcb": Selector(conditions={"type": "pcb_board", "size": "120x100mm"}, num=1),
                "paste": Selector(conditions={"type": "solder_paste"}, num=1),
            },
            consume_batch={
                "printer": Selector(conditions={"type": "solder_printer_2", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            produce={"printed": Selector(conditions={"type": "paste_applied_pcb"}, num=1)},
            produce_batch={
                "printer": Selector(conditions={"type": "solder_printer_2", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            duration_s=40.0, duration_batch_s=180.0,
            batch_min=3, batch_max=15,
        ),
        # 3. Pick & place — line 1
        Rule(
            rule_id="place_1",
            consume={
                "pcb": Selector(conditions={"type": "paste_applied_pcb"}, num=1),
                "chip": Selector(conditions={"type": "silicon_chip", "part": "mcu_32bit"}, num=1),
                "cap": Selector(conditions={"type": "capacitor", "value": "100nF"}, num=5),
                "res": Selector(conditions={"type": "resistor", "value": "1k"}, num=4),
            },
            consume_batch={
                "pnp": Selector(conditions={"type": "pick_and_place_1", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            produce={"pop": Selector(conditions={"type": "populated_pcb"}, num=1)},
            produce_batch={
                "pnp": Selector(conditions={"type": "pick_and_place_1", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            duration_s=60.0, duration_batch_s=300.0,  # feeder changeover
            batch_min=5, batch_max=30,
        ),
        # 4. Pick & place — line 2 (flex, for DSP)
        Rule(
            rule_id="place_2",
            consume={
                "pcb": Selector(conditions={"type": "paste_applied_pcb"}, num=1),
                "chip": Selector(conditions={"type": "silicon_chip", "part": "sensor_dsp"}, num=1),
                "cap": Selector(conditions={"type": "capacitor", "value": "10uF"}, num=3),
                "res": Selector(conditions={"type": "resistor", "value": "1k"}, num=2),
                "conn": Selector(conditions={"type": "connector", "model": "usb_c"}, num=1),
            },
            consume_batch={
                "pnp": Selector(conditions={"type": "pick_and_place_2", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            produce={"pop": Selector(conditions={"type": "populated_pcb"}, num=1)},
            produce_batch={
                "pnp": Selector(conditions={"type": "pick_and_place_2", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            duration_s=90.0, duration_batch_s=600.0,
            batch_min=3, batch_max=15,
        ),
        # 5. Reflow — oven 1
        Rule(
            rule_id="reflow_1",
            consume={"pcb": Selector(conditions={"type": "populated_pcb"}, num=1)},
            consume_batch={
                "oven": Selector(conditions={"type": "reflow_oven_1", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            produce={"refl": Selector(conditions={"type": "reflowed_pcb"}, num=1)},
            produce_batch={
                "oven": Selector(conditions={"type": "reflow_oven_1", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            duration_s=90.0, duration_batch_s=0,
            batch_min=5, batch_max=30,
        ),
        # 6. Reflow — oven 2
        Rule(
            rule_id="reflow_2",
            consume={"pcb": Selector(conditions={"type": "populated_pcb"}, num=1)},
            consume_batch={
                "oven": Selector(conditions={"type": "reflow_oven_2", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            produce={"refl": Selector(conditions={"type": "reflowed_pcb"}, num=1)},
            produce_batch={
                "oven": Selector(conditions={"type": "reflow_oven_2", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            duration_s=120.0, duration_batch_s=0,
            batch_min=3, batch_max=15,
        ),
        # 7. AOI inspection
        Rule(
            rule_id="aoi_inspect",
            consume={"pcb": Selector(conditions={"type": "reflowed_pcb"}, num=1)},
            consume_batch={
                "aoi": Selector(conditions={"type": "aoi_machine", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            produce={"insp": Selector(conditions={"type": "tested_module"}, num=1)},
            produce_batch={
                "aoi": Selector(conditions={"type": "aoi_machine", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            duration_s=30.0, duration_batch_s=0,
            batch_min=5, batch_max=30,
        ),
        # 8. Wave solder (through-hole components)
        Rule(
            rule_id="wave_solder_th",
            consume={
                "pcb": Selector(conditions={"type": "tested_module"}, num=1),
                "conn": Selector(conditions={"type": "connector", "model": "rj45"}, num=1),
            },
            consume_batch={
                "wave": Selector(conditions={"type": "wave_solder", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            produce={"wave": Selector(conditions={"type": "wave_soldered_module"}, num=1)},
            produce_batch={
                "wave": Selector(conditions={"type": "wave_solder", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            duration_s=60.0, duration_batch_s=120.0,
            batch_min=3, batch_max=20,
        ),
        # 9. Conformal coating
        Rule(
            rule_id="conformal_coat",
            consume={
                "pcb": Selector(conditions={"type": "wave_soldered_module"}, num=1),
                "coat": Selector(conditions={"type": "coating_material"}, num=1),
            },
            consume_batch={
                "robot": Selector(conditions={"type": "coating_robot", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            produce={"coat": Selector(conditions={"type": "coated_module"}, num=1)},
            produce_batch={
                "robot": Selector(conditions={"type": "coating_robot", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "smt"}),
            },
            duration_s=30.0, duration_batch_s=60.0,
            batch_min=3, batch_max=20,
        ),
        # 10. Final assembly + functional test — bench 1
        # Assembly and QC are combined to avoid pass-through rule overhead
        # in the greedy solver.
        Rule(
            rule_id="assemble_controller",
            consume={
                "module": Selector(conditions={"type": "coated_module"}, num=1),
                "enclosure": Selector(conditions={"type": "enclosure", "model": "abs_black"}, num=1),
                "harness": Selector(conditions={"type": "wire_harness"}, num=1),
            },
            consume_batch={
                "bench": Selector(conditions={"type": "assembly_bench_1", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "assembly"}),
            },
            produce={"product": Selector(conditions={"type": "assembled_controller"}, num=1)},
            produce_batch={
                "bench": Selector(conditions={"type": "assembly_bench_1", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "assembly"}),
            },
            duration_s=60.0, duration_batch_s=30.0,
            batch_min=1, batch_max=20,
        ),
        # 11. Final assembly + test — bench 2
        Rule(
            rule_id="assemble_sensor",
            consume={
                "module": Selector(conditions={"type": "coated_module"}, num=1),
                "enclosure": Selector(conditions={"type": "enclosure", "model": "abs_grey"}, num=1),
                "harness": Selector(conditions={"type": "wire_harness"}, num=1),
            },
            consume_batch={
                "bench": Selector(conditions={"type": "assembly_bench_2", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "assembly"}),
            },
            produce={"product": Selector(conditions={"type": "sensor_module"}, num=1)},
            produce_batch={
                "bench": Selector(conditions={"type": "assembly_bench_2", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "assembly"}),
            },
            duration_s=90.0, duration_batch_s=60.0,
            batch_min=1, batch_max=15,
        ),
    ]

    orders: list[Order] = [
        Order(
            order_id="ORD-CTRL-001",
            consume={"product": Selector(conditions={"type": "assembled_controller"}, num=50)},
            deadline=_dt(days=14),
            late_delivery_penalty_per_s=5.0,
        ),
        Order(
            order_id="ORD-SENS-001",
            consume={"product": Selector(conditions={"type": "sensor_module"}, num=30)},
            deadline=_dt(days=10),
            late_delivery_penalty_per_s=8.0,
        ),
        Order(
            order_id="ORD-CTRL-002",
            consume={"product": Selector(conditions={"type": "assembled_controller"}, num=80)},
            deadline=_dt(days=28),
            late_delivery_penalty_per_s=5.0,
        ),
        Order(
            order_id="ORD-SENS-002",
            consume={"product": Selector(conditions={"type": "sensor_module"}, num=40)},
            deadline=_dt(days=35),
            late_delivery_penalty_per_s=10.0,
            early_delivery_bonus_per_s=3.0,
        ),
    ]

    return PlanningModel(
        entities=entities,
        rules=rules,
        orders=orders,
        holding_rules=holding_rules,
        objective=Objective(expression="$money_cent_remaining", expiry_loss_decay_factor=0.5),
        planning_start=PLANNING_START,
        planning_horizon_s=86400 * 45,
    )
