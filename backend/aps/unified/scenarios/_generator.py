"""Random scenario generator — build rich PlanningModel instances with specifiable complexity.

The generator creates multi-stage manufacturing processes where raw materials
are transformed through several production stages into final products.

Complexity is controlled by:
- ``num_machine_types`` / ``machines_per_type`` — how much equipment
- ``num_raw_materials`` / ``num_final_products`` — breadth of BOM
- ``bom_depth`` — how many transformation steps (2 = raw → part → product,
  3 = raw → sub-assembly → assembly → product, etc.)
- ``rules_per_stage`` — parallel processing options at each stage
- ``num_operators`` — human resource constraints
- ``num_orders`` — how many demand signals to schedule
"""

from __future__ import annotations

import itertools
import random
from datetime import UTC, datetime, timedelta

from aps.unified._schema import Entity, Objective, Order, PlanningModel, Rule, Selector

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_entity(type_name: str, count: int = 1, **extra: object) -> Entity:
    """Create a single entity with ``type`` and optional extra fields."""
    fields: dict[str, str | int | float | bool | datetime] = {"type": type_name}
    for k, v in extra.items():
        if isinstance(v, (str, int, float, bool, datetime)):
            fields[k] = v
    return Entity(fields=fields, count=count)


def _make_selector(type_name: str, num: float = 1.0, **extra: object) -> Selector:
    """Create a selector matching entities of ``type`` with extra conditions."""
    conditions: dict[str, str | int | float | bool | datetime] = {"type": type_name}
    for k, v in extra.items():
        if isinstance(v, (str, int, float, bool, datetime)):
            conditions[k] = v
    return Selector(conditions=conditions, num=num)


# ── Material palettes (themed by scenario) ────────────────────────────────────

MATERIAL_PALETTES: dict[str, tuple[list[str], list[str], list[str]]] = {
    # (raw_materials, intermediate_parts, products)
    "electronics": (
        ["pcb_board", "solder_paste", "silicon_chip", "capacitor", "resistor", "connector"],
        ["paste_applied_pcb", "populated_pcb", "reflowed_pcb", "tested_module"],
        ["assembled_controller", "power_supply_unit", "sensor_module"],
    ),
    "metalworking": (
        ["steel_bar", "aluminum_bar", "steel_sheet", "aluminum_sheet", "copper_wire", "cast_iron_ingot"],
        ["cut_part", "machined_part", "drilled_part", "ground_part", "heat_treated_part"],
        ["precision_shaft", "gear_assembly", "bracket_set", "housing_unit"],
    ),
    "assembly": (
        ["frame_chassis", "electric_motor", "wheel_set", "controller_board", "battery_pack", "wire_harness"],
        ["powered_frame", "rolling_frame", "wired_frame", "sub_assembly_drive"],
        ["finished_vehicle", "completed_robot", "final_machine"],
    ),
    "automotive": (
        ["steel_coil", "aluminum_coil", "welding_wire", "primer_paint", "sealant"],
        ["stamped_hood", "stamped_door", "stamped_fender", "welded_body", "painted_body"],
        ["body_in_white", "finished_body_panel_set"],
    ),
    "furniture": (
        ["wood_panel_oak", "wood_panel_walnut", "edging_tape", "hardware_kit", "varnish", "plywood_sheet"],
        ["cut_panel", "edged_panel", "drilled_panel", "sanded_panel", "finished_panel"],
        ["oak_cabinet", "walnut_desk", "plywood_shelf_set", "custom_table"],
    ),
    "medical": (
        ["medical_grade_plastic", "electronic_module", "sensor_element", "sterile_tubing", "fastener_set"],
        ["molded_plastic_part", "assembled_unit", "sterilized_device", "tested_device"],
        ["diagnostic_device", "monitoring_sensor", "surgical_tool_set"],
    ),
    "food": (
        ["flour", "sugar", "butter", "eggs", "chocolate", "vanilla_extract"],
        ["mixed_batter", "baked_goods", "cooled_product", "iced_product"],
        ["packaged_cookies", "premium_chocolate_box", "artisan_bread_loaf"],
    ),
    "pharma": (
        ["api_powder_a", "api_powder_b", "excipient_binder", "excipient_filler", "coating_polymer", "purified_water"],
        ["granulated_blend", "compressed_core", "coated_tablet", "blister_pack"],
        ["finished_drug_batch", "qc_released_batch"],
    ),
    "semiconductor": (
        ["silicon_wafer", "photoresist", "etch_gas", "cvd_precursor", "cmp_slurry", "dopant_source"],
        ["coated_wafer", "exposed_wafer", "etched_wafer", "deposited_wafer", "planarized_wafer"],
        ["finished_die", "packaged_chip", "tested_device"],
    ),
}


def _equipment_names(machine_type: str, count: int) -> list[str]:
    """Generate realistic equipment names for a machine type."""
    prefix_map = {
        "printer": ("solder_printer", "dispensing_system"),
        "picker": ("pick_and_place", "chip_shooter"),
        "oven": ("reflow_oven", "curing_tunnel"),
        "inspection": ("aoi_machine", "xray_inspector"),
        "lathe": ("cnc_lathe", "turning_center"),
        "mill": ("cnc_mill", "machining_center"),
        "drill": ("drill_press", "cnc_drill"),
        "grinder": ("surface_grinder", "cylindrical_grinder"),
        "stamping_press": ("stamping_press", "hydraulic_press"),
        "welding_robot": ("welding_robot", "spot_welder"),
        "conveyor": ("assembly_conveyor", "transfer_line"),
        "robot": ("industrial_robot", "cobot"),
        "oven_food": ("industrial_oven", "proofer"),
        "mixer": ("planetary_mixer", "spiral_mixer"),
        "packaging": ("packaging_machine", "flow_wrapper"),
        "cnc_router": ("cnc_router", "cnc_router"),
        "edge_bander": ("edge_bander", "edge_banding_machine"),
        "saw": ("panel_saw", "beam_saw"),
        "sterilizer": ("autoclave", "uv_sterilizer"),
        "cleanroom": ("cleanroom_assembly_station", "cleanroom_bench"),
        "qc_station": ("qc_test_station", "inspection_bench"),
        "mold": ("injection_molder", "compression_molder"),
        "stamping": ("stamping_press", "coining_press"),
        "fermenter": ("fermentation_tank", "bioreactor"),
        "centrifuge": ("centrifuge_a", "centrifuge_b"),
        "chromatography": ("chromatography_column", "purification_skid"),
        "lyophilizer": ("freeze_dryer_a", "freeze_dryer_b"),
        "tablet_press": ("tablet_press_a", "tablet_press_b"),
        "coater": ("coating_pan_a", "coating_pan_b"),
        "stepper": ("lithography_stepper", "scanner"),
        "etcher": ("dry_etcher", "wet_bench"),
        "furnace": ("diffusion_furnace_a", "diffusion_furnace_b"),
        "tester": ("wafer_prober", "final_tester"),
        "cmp_tool": ("cmp_polisher_a", "cmp_polisher_b"),
    }
    names = prefix_map.get(machine_type, (machine_type, f"{machine_type}_secondary"))
    return [f"{names[i % len(names)]}_{i + 1:02d}" for i in range(count)]


# ── ScenarioGenerator ─────────────────────────────────────────────────────────


class ScenarioGenerator:
    """Build complex PlanningModel scenarios with controllable complexity.

    Usage::

        gen = ScenarioGenerator(seed=42)
        model = gen.generate(
            scenario_id="my_scenario",
            name="My Scenario",
            description="A complex manufacturing process",
            palette="electronics",
            num_machine_types=4,
            machines_per_type=2,
            bom_depth=3,
            rules_per_stage=2,
            num_orders=3,
        )
    """

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)
        self.entity_counter = itertools.count(1)

    def _next_eid(self) -> str:
        return f"e{next(self.entity_counter):05d}"

    # ── Main generate method ─────────────────────────────────────────────

    def generate(
        self,
        *,
        # Palette
        palette: str = "metalworking",
        # Equipment
        num_machine_types: int = 2,
        machines_per_type: int = 1,
        # BOM
        bom_depth: int = 2,
        num_raw_materials: int = 3,
        num_final_products: int = 2,
        # Rules
        rules_per_stage: int = 1,
        duration_per_unit_range: tuple[int, int] = (30, 180),
        duration_batch_range: tuple[int, int] = (0, 30),
        batch_min: int = 1,
        batch_max: int = 20,
        # Operators
        num_operators: int = 0,
        # Orders
        num_orders: int = 2,
        order_qty_range: tuple[int, int] = (5, 30),
        # Horizon
        horizon_days: int = 30,
        # Batch size limit (auto-capped to prevent greedy over-consumption)
        batch_max_limit: int | None = None,
        # Difficulty modifiers
        setup_times: bool = False,
    ) -> PlanningModel:
        """Generate a rich, random PlanningModel.

        The BOM is a tree:

        - Level 0: raw materials (``num_raw_materials``)
        - Level 1 .. ``bom_depth``-1: intermediate products
        - Level ``bom_depth``: final products (``num_final_products``)

        Each level transition has ``rules_per_stage`` parallel rules consuming
        from the previous level and producing to the next.
        """
        palette_data = MATERIAL_PALETTES.get(palette, MATERIAL_PALETTES["metalworking"])
        raw_names, inter_names, product_names = palette_data

        # Clamp available names
        raw_names = raw_names[:num_raw_materials]
        inter_names = inter_names[:max(4, num_final_products)]
        product_names = product_names[:num_final_products]

        # Extended list for intermediate levels
        self.rng.shuffle(raw_names)
        self.rng.shuffle(inter_names)
        self.rng.shuffle(product_names)

        entities: list[Entity] = []
        rules: list[Rule] = []
        orders: list[Order] = []

        # ── Machine types ────────────────────────────────────────────────
        machine_type_names = [
            f"machine_{chr(ord('A') + i)}" for i in range(num_machine_types)
        ]
        machine_entities: dict[str, list[Entity]] = {}
        for mt in machine_type_names:
            machines = []
            for eq_name in _equipment_names(mt, machines_per_type):
                machines.append(
                    _make_entity(mt, entity_id=eq_name, state="idle", location="plant")
                )
            machine_entities[mt] = machines
            entities.extend(machines)

        # ── Raw materials ────────────────────────────────────────────────
        # Scale raw material quantities to support multi-level BOM chains.
        # Each rule at each stage consumes per-unit, so we need enough for
        # all downstream production.
        estimated_total_need = (
            num_final_products
            * rules_per_stage
            * max(order_qty_range)
            * (bom_depth ** 2)
        ) * 2  # 2x safety margin
        for name in raw_names:
            qty = max(estimated_total_need, self.rng.randint(50, 200))
            location = self.rng.choice(["warehouse_1", "warehouse_2", "warehouse_3"])
            entities.append(
                Entity(fields={"type": name, "location": location}, count=qty)
            )

        # ── Operators (optional) ─────────────────────────────────────────
        operator_entities: list[Entity] = []
        operator_names_pool = ["alice", "bob", "charlie", "diana", "eve", "frank", "grace", "henry"]
        if num_operators > 0:
            for i in range(num_operators):
                name = operator_names_pool[i % len(operator_names_pool)]
                skill_level = self.rng.choice(["junior", "mid", "senior"])
                operator_entities.append(
                    _make_entity("operator", name=name, skill=skill_level, shift="day")
                )
            entities.extend(operator_entities)

        # ── BOM structure ────────────────────────────────────────────────
        # We build a tree: level 0 = raw, level depth = final product
        # Each intermediate level produces "assembly" type entities.

        level_types: dict[int, list[str]] = {0: raw_names.copy()}

        for level in range(1, bom_depth + 1):
            if level < bom_depth:
                # Intermediate level
                num_types = max(1, min(4, num_final_products))
                names = inter_names[:num_types]
                # Alternate with level-specific names
                level_names = [f"stage{level}_{n}" for n in names]
            else:
                # Final products
                level_names = product_names.copy()
            level_types[level] = level_names

        # ── Rules for each stage ─────────────────────────────────────────
        rule_idx = 0

        for level in range(1, bom_depth + 1):
            inputs = level_types[level - 1]
            outputs = level_types[level]

            for product_out in outputs:
                # Each product needs rules_per_stage alternative rules
                for variant in range(rules_per_stage):
                    rule_idx += 1
                    rule_id = f"{product_out}_v{variant}" if variant > 0 else product_out

                    # Pick input materials
                    num_inputs = min(self.rng.randint(1, max(1, len(inputs))), len(inputs))
                    stage_inputs = self.rng.sample(inputs, num_inputs)

                    # Pick a machine type
                    machine_type = self.rng.choice(machine_type_names)

                    # Duration
                    dur_unit = self.rng.randint(*duration_per_unit_range)
                    dur_batch = self.rng.randint(*duration_batch_range) if setup_times else 0

                    consume_dict: dict[str, Selector] = {}
                    consume_batch_dict: dict[str, Selector] = {
                        "machine": _make_selector(machine_type, state="idle"),
                    }

                    produce_dict: dict[str, Selector] = {
                        "output": _make_selector(product_out),
                    }
                    produce_batch_dict: dict[str, Selector] = {
                        "machine": _make_selector(machine_type, state="idle"),
                    }

                    # Consume inputs
                    for inp in stage_inputs:
                        qty_per = self.rng.randint(1, 3)
                        consume_dict[inp] = _make_selector(inp, num=float(qty_per))

                    # Optional operator consume/produce
                    if num_operators > 0 and self.rng.random() < 0.7:
                        op = self.rng.choice(operator_entities)
                        op_type = "operator"
                        consume_batch_dict["operator"] = _make_selector(
                            op_type,
                            name=op.fields.get("name", "operator"),
                        )
                        produce_batch_dict["operator"] = _make_selector(
                            op_type,
                            name=op.fields.get("name", "operator"),
                        )

                    rules.append(
                        Rule(
                            rule_id=rule_id,
                            batch_min=batch_min,
                            batch_max=min(batch_max, batch_max_limit) if batch_max_limit is not None else batch_max,
                            consume=consume_dict,
                            consume_batch=consume_batch_dict,
                            produce=produce_dict,
                            produce_batch=produce_batch_dict,
                            duration_s=float(dur_unit),
                            duration_batch_s=float(dur_batch),
                        )
                    )

        # ── Orders ───────────────────────────────────────────────────────
        planning_start = datetime(2026, 7, 24, tzinfo=UTC)
        horizon_s = 86400 * horizon_days

        for i in range(num_orders):
            if not product_names:
                break
            product = product_names[i % len(product_names)]
            qty = self.rng.randint(*order_qty_range)

            deadline_offset_days = self.rng.randint(max(1, horizon_days // 4), horizon_days)
            deadline = planning_start + timedelta(days=deadline_offset_days)

            orders.append(
                Order(
                    order_id=f"ORD-{i + 1:03d}",
                    consume={"product": _make_selector(product, num=float(qty))},
                    deadline=deadline,
                    late_delivery_penalty_per_s=float(self.rng.randint(1, 10)),
                )
            )

        # ── Assemble model ───────────────────────────────────────────────
        return PlanningModel(
            entities=entities,
            rules=rules,
            orders=orders,
            objective=Objective(expression="$money_cent_remaining"),
            planning_start=planning_start,
            planning_horizon_s=horizon_s,
        )


# ── Convenience: build with tiered complexity ───────────────────────────────


def generate_with_complexity(
    level: int = 1,
    seed: int = 0,
    **overrides: object,
) -> PlanningModel:
    """Generate a scenario with a named complexity tier.

    ``level`` is 1 (simple) through 5 (very complex).  Keyword overrides
    are passed through to ``ScenarioGenerator.generate()``.
    """
    tiers: dict[int, dict[str, object]] = {
        1: dict(
            num_machine_types=2,
            machines_per_type=1,
            bom_depth=2,
            num_raw_materials=2,
            num_final_products=1,
            rules_per_stage=1,
            num_operators=0,
            num_orders=1,
            order_qty_range=(5, 15),
            duration_per_unit_range=(30, 120),
            setup_times=False,
        ),
        2: dict(
            num_machine_types=3,
            machines_per_type=1,
            bom_depth=2,
            num_raw_materials=3,
            num_final_products=2,
            rules_per_stage=1,
            num_operators=1,
            num_orders=2,
            order_qty_range=(10, 30),
            duration_per_unit_range=(30, 180),
            setup_times=False,
        ),
        3: dict(
            num_machine_types=3,
            machines_per_type=2,
            bom_depth=3,
            num_raw_materials=4,
            num_final_products=2,
            rules_per_stage=2,
            num_operators=2,
            num_orders=3,
            order_qty_range=(10, 50),
            duration_per_unit_range=(30, 300),
            setup_times=True,
        ),
        4: dict(
            num_machine_types=4,
            machines_per_type=2,
            bom_depth=3,
            num_raw_materials=5,
            num_final_products=3,
            rules_per_stage=2,
            num_operators=3,
            num_orders=4,
            order_qty_range=(15, 80),
            duration_per_unit_range=(60, 600),
            setup_times=True,
        ),
        5: dict(
            num_machine_types=5,
            machines_per_type=2,
            bom_depth=4,
            num_raw_materials=6,
            num_final_products=4,
            rules_per_stage=3,
            num_operators=4,
            num_orders=5,
            order_qty_range=(20, 100),
            duration_per_unit_range=(60, 900),
            setup_times=True,
        ),
    }

    params = dict(tiers.get(level, tiers[1]))
    params.update(overrides)
    gen = ScenarioGenerator(seed=seed)
    return gen.generate(**params)  # type: ignore[arg-type]
