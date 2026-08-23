"""Semiconductor fabrication — re-entrant flow, batch tools, PM windows.

Scenario: A wafer fab producing integrated circuits:
- Front-end-of-line (FEOL): oxidation, photolithography, etch, deposition
- Back-end-of-line (BEOL): CMP planarization, metal deposition, passivation
- Re-entrant flow: wafers revisit the same tool types at different process steps
- Batch tools (furnace/oxidation) process multiple lots together
- Preventive maintenance windows on critical tools (stepper, etcher)
- Reticle/recipe constraints — each stepper uses specific reticles
- Holding rules for WIP between operations
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

SCENARIO_ID = "semiconductor_fab"
SCENARIO_NAME = "Semiconductor Wafer Fabrication"
SCENARIO_DESCRIPTION = (
    "Wafer fab with re-entrant flow: 19 rules across oxidation, lithography, "
    "etch, deposition, CMP, testing. 2 product masks (PMIC, logic), "
    "furnace batch tools (6-wafer lots), stepper reticle constraints, "
    "PM windows on critical equipment, re-entrant flow (wafers revisit etcher "
    "at 3 different steps), WIP holding costs, dual equipment."
)

PLANNING_START = datetime(2026, 7, 24, tzinfo=UTC)


def _dt(days: int = 0, hours: int = 0) -> datetime:
    return PLANNING_START + timedelta(days=days, hours=hours)


def generate(*, seed: int = 0) -> PlanningModel:
    _ = seed

    entities: list[Entity] = [
        # Raw wafers
        Entity(fields={"type": "silicon_wafer", "diameter": "200mm", "grade": "prime",
                       "location": "fab_stocker"}, count=300),
        Entity(fields={"type": "silicon_wafer", "diameter": "200mm", "grade": "test",
                       "location": "fab_stocker"}, count=50),
        # Consumables
        Entity(fields={"type": "photoresist", "lob": "positive", "location": "chemical_cabinet"}, count=200),
        Entity(fields={"type": "photoresist", "lob": "negative", "location": "chemical_cabinet"}, count=100),
        Entity(fields={"type": "etch_gas", "chemistry": "fluorine", "location": "gas_bunker"}, count=100),
        Entity(fields={"type": "etch_gas", "chemistry": "chlorine", "location": "gas_bunker"}, count=80),
        Entity(fields={"type": "cvd_precursor", "material": "oxide", "location": "chemical_cabinet"}, count=150),
        Entity(fields={"type": "cvd_precursor", "material": "nitride", "location": "chemical_cabinet"}, count=100),
        Entity(fields={"type": "cmp_slurry", "grade": "oxide_cmp", "location": "slurry_feed"}, count=200),
        Entity(fields={"type": "dopant_source", "dopant": "boron", "location": "implant_store"}, count=80),
        Entity(fields={"type": "dopant_source", "dopant": "phosphorus", "location": "implant_store"}, count=80),
    ]

    # ── Equipment — 12 pieces ───────────────────────────────────────────
    entities += [
        Entity(fields={"type": "oxidation_furnace_a", "state": "idle",
                       "location": "diffusion_bay", "capacity_batch": "6"}),
        Entity(fields={"type": "oxidation_furnace_b", "state": "idle",
                       "location": "diffusion_bay", "capacity_batch": "6"}),
        Entity(fields={"type": "stepper_1", "state": "idle", "location": "litho_bay", "reticles": "pmic"}),
        Entity(fields={"type": "stepper_2", "state": "idle", "location": "litho_bay", "reticles": "logic"}),
        Entity(fields={"type": "stepper_3", "state": "idle", "location": "litho_bay", "reticles": "both"}),
        Entity(fields={"type": "dry_etcher_a", "state": "idle", "location": "etch_bay", "chemistry": "fluorine"}),
        Entity(fields={"type": "dry_etcher_b", "state": "idle", "location": "etch_bay", "chemistry": "chlorine"}),
        Entity(fields={"type": "dry_etcher_c", "state": "idle", "location": "etch_bay", "chemistry": "both"}),
        Entity(fields={"type": "cvd_deposition_a", "state": "idle", "location": "dep_bay", "material": "oxide"}),
        Entity(fields={"type": "cvd_deposition_b", "state": "idle", "location": "dep_bay", "material": "nitride"}),
        Entity(fields={"type": "cmp_polisher_a", "state": "idle", "location": "cmp_bay"}),
        Entity(fields={"type": "cmp_polisher_b", "state": "idle", "location": "cmp_bay"}),
        Entity(fields={"type": "wafer_prober", "state": "idle", "location": "test_bay"}),
        Entity(fields={"type": "final_tester", "state": "idle", "location": "test_bay"}),
        Entity(fields={"type": "operator", "cert": "diffusion", "shift": "day"}, count=2),
        Entity(fields={"type": "operator", "cert": "litho", "shift": "day"}, count=2),
        Entity(fields={"type": "operator", "cert": "etch", "shift": "day"}, count=2),
        Entity(fields={"type": "operator", "cert": "deposition", "shift": "day"}, count=2),
        Entity(fields={"type": "operator", "cert": "cmp", "shift": "day"}, count=1),
        Entity(fields={"type": "operator", "cert": "test", "shift": "day"}, count=1),
    ]

    # ── Holding rules ───────────────────────────────────────────────────
    holding_rules: list[HoldingRule] = [
        HoldingRule(
            selector=Selector(conditions={"type": "coated_wafer"}),
            max=100.0,
        ),
        HoldingRule(
            selector=Selector(conditions={"type": "deposited_wafer"}),
            max=150.0,
        ),
    ]

    # ── Rules — 18 rules ────────────────────────────────────────────────

    # ── Stage 1: Oxidation (FEOL) ──
    rules: list[Rule] = [
        # 1. Furnace A — batch oxidation (6 wafers)
        Rule(
            rule_id="oxidation_a",
            consume={"wafer": Selector(conditions={"type": "silicon_wafer", "diameter": "200mm"}, num=6)},
            consume_batch={
                "furnace": Selector(conditions={"type": "oxidation_furnace_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "diffusion"}),
            },
            produce={"ox": Selector(conditions={"type": "coated_wafer"}, num=6)},
            produce_batch={
                "furnace": Selector(conditions={"type": "oxidation_furnace_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "diffusion"}),
            },
            duration_s=600.0,
            duration_batch_s=1200.0,  # ramping
            batch_min=1, batch_max=1,  # furnace is batch-fixed at 6 wafers
        ),
        # 2. Furnace B
        Rule(
            rule_id="oxidation_b",
            consume={"wafer": Selector(conditions={"type": "silicon_wafer", "diameter": "200mm"}, num=6)},
            consume_batch={
                "furnace": Selector(conditions={"type": "oxidation_furnace_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "diffusion"}),
            },
            produce={"ox": Selector(conditions={"type": "coated_wafer"}, num=6)},
            produce_batch={
                "furnace": Selector(conditions={"type": "oxidation_furnace_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "diffusion"}),
            },
            duration_s=600.0,
            duration_batch_s=1200.0,
            batch_min=1, batch_max=1,
        ),
        # ── Stage 2: Photoresist coat ──
        # Uses the coated_wafer from oxidation
        Rule(
            rule_id="coat_photoresist",
            consume={
                "wafer": Selector(conditions={"type": "coated_wafer"}, num=1),
                "resist": Selector(conditions={"type": "photoresist", "lob": "positive"}, num=1),
            },
            consume_batch={
                "operator": Selector(conditions={"type": "operator", "cert": "litho"}),
            },
            produce={"coated": Selector(conditions={"type": "coated_wafer"}, num=1)},
            produce_batch={
                "operator": Selector(conditions={"type": "operator", "cert": "litho"}),
            },
            duration_s=120.0,
            duration_batch_s=60.0,
            batch_min=3, batch_max=12,
        ),
        # ── Stage 3: Lithography (3 steppers) ──
        # 3. Stepper 1 — PMIC mask
        Rule(
            rule_id="expose_pmic",
            consume={"wafer": Selector(conditions={"type": "coated_wafer"}, num=1)},
            consume_batch={
                "stepper": Selector(conditions={"type": "stepper_1", "state": "idle", "reticles": "pmic"}),
                "operator": Selector(conditions={"type": "operator", "cert": "litho"}),
            },
            produce={"exp": Selector(conditions={"type": "exposed_wafer"}, num=1)},
            produce_batch={
                "stepper": Selector(conditions={"type": "stepper_1", "state": "idle", "reticles": "pmic"}),
                "operator": Selector(conditions={"type": "operator", "cert": "litho"}),
            },
            duration_s=180.0,
            duration_batch_s=120.0,  # reticle load and alignment
            batch_min=3, batch_max=12,
        ),
        # 4. Stepper 2 — Logic mask
        Rule(
            rule_id="expose_logic",
            consume={"wafer": Selector(conditions={"type": "coated_wafer"}, num=1)},
            consume_batch={
                "stepper": Selector(conditions={"type": "stepper_2", "state": "idle", "reticles": "logic"}),
                "operator": Selector(conditions={"type": "operator", "cert": "litho"}),
            },
            produce={"exp": Selector(conditions={"type": "exposed_wafer"}, num=1)},
            produce_batch={
                "stepper": Selector(conditions={"type": "stepper_2", "state": "idle", "reticles": "logic"}),
                "operator": Selector(conditions={"type": "operator", "cert": "litho"}),
            },
            duration_s=180.0,
            duration_batch_s=120.0,
            batch_min=3, batch_max=12,
        ),
        # 5. Stepper 3 — Both masks (flexible)
        Rule(
            rule_id="expose_flex",
            consume={"wafer": Selector(conditions={"type": "coated_wafer"}, num=1)},
            consume_batch={
                "stepper": Selector(conditions={"type": "stepper_3", "state": "idle", "reticles": "both"}),
                "operator": Selector(conditions={"type": "operator", "cert": "litho"}),
            },
            produce={"exp": Selector(conditions={"type": "exposed_wafer"}, num=1)},
            produce_batch={
                "stepper": Selector(conditions={"type": "stepper_3", "state": "idle", "reticles": "both"}),
                "operator": Selector(conditions={"type": "operator", "cert": "litho"}),
            },
            duration_s=200.0,
            duration_batch_s=180.0,  # reticle change takes longer
            batch_min=3, batch_max=6,
        ),
        # ── Stage 4: Develop (re-entrant: same type as coated_wafer output) ──
        Rule(
            rule_id="develop_wafer",
            consume={"wafer": Selector(conditions={"type": "exposed_wafer"}, num=1)},
            consume_batch={
                "operator": Selector(conditions={"type": "operator", "cert": "litho"}),
            },
            produce={"dev": Selector(conditions={"type": "coated_wafer"}, num=1)},
            produce_batch={
                "operator": Selector(conditions={"type": "operator", "cert": "litho"}),
            },
            duration_s=60.0,
            batch_min=3, batch_max=12,
        ),
        # ── Stage 5: Etch (re-entrant: 3 etchers, 3 chemistries) ──
        # 6. Etcher A — fluorine chemistry
        Rule(
            rule_id="etch_fluorine",
            consume={
                "wafer": Selector(conditions={"type": "coated_wafer"}, num=1),
                "gas": Selector(conditions={"type": "etch_gas", "chemistry": "fluorine"}, num=1),
            },
            consume_batch={
                "etcher": Selector(conditions={"type": "dry_etcher_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "etch"}),
            },
            produce={"etched": Selector(conditions={"type": "etched_wafer"}, num=1)},
            produce_batch={
                "etcher": Selector(conditions={"type": "dry_etcher_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "etch"}),
            },
            duration_s=180.0,
            duration_batch_s=300.0,  # chamber conditioning
            batch_min=3, batch_max=12,
        ),
        # 7. Etcher B — chlorine chemistry
        Rule(
            rule_id="etch_chlorine",
            consume={
                "wafer": Selector(conditions={"type": "coated_wafer"}, num=1),
                "gas": Selector(conditions={"type": "etch_gas", "chemistry": "chlorine"}, num=1),
            },
            consume_batch={
                "etcher": Selector(conditions={"type": "dry_etcher_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "etch"}),
            },
            produce={"etched": Selector(conditions={"type": "etched_wafer"}, num=1)},
            produce_batch={
                "etcher": Selector(conditions={"type": "dry_etcher_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "etch"}),
            },
            duration_s=180.0,
            duration_batch_s=300.0,
            batch_min=3, batch_max=12,
        ),
        # 8. Etcher C — both chemistries (flex)
        Rule(
            rule_id="etch_flex",
            consume={
                "wafer": Selector(conditions={"type": "coated_wafer"}, num=1),
                "gas": Selector(conditions={"type": "etch_gas", "chemistry": "fluorine"}, num=1),
            },
            consume_batch={
                "etcher": Selector(conditions={"type": "dry_etcher_c", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "etch"}),
            },
            produce={"etched": Selector(conditions={"type": "etched_wafer"}, num=1)},
            produce_batch={
                "etcher": Selector(conditions={"type": "dry_etcher_c", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "etch"}),
            },
            duration_s=200.0,
            duration_batch_s=600.0,  # longer gas changeover
            batch_min=3, batch_max=6,
        ),
        # ── Stage 6: CVD Deposition ──
        # 9. Dep A — oxide
        Rule(
            rule_id="dep_oxide",
            consume={
                "wafer": Selector(conditions={"type": "etched_wafer"}, num=1),
                "precursor": Selector(conditions={"type": "cvd_precursor", "material": "oxide"}, num=1),
            },
            consume_batch={
                "dep": Selector(conditions={"type": "cvd_deposition_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "deposition"}),
            },
            produce={"deposited": Selector(conditions={"type": "deposited_wafer"}, num=1)},
            produce_batch={
                "dep": Selector(conditions={"type": "cvd_deposition_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "deposition"}),
            },
            duration_s=300.0,
            duration_batch_s=600.0,  # pump-down, temperature stabilization
            batch_min=3, batch_max=12,
        ),
        # 10. Dep B — nitride
        Rule(
            rule_id="dep_nitride",
            consume={
                "wafer": Selector(conditions={"type": "etched_wafer"}, num=1),
                "precursor": Selector(conditions={"type": "cvd_precursor", "material": "nitride"}, num=1),
            },
            consume_batch={
                "dep": Selector(conditions={"type": "cvd_deposition_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "deposition"}),
            },
            produce={"deposited": Selector(conditions={"type": "deposited_wafer"}, num=1)},
            produce_batch={
                "dep": Selector(conditions={"type": "cvd_deposition_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "deposition"}),
            },
            duration_s=400.0,
            duration_batch_s=600.0,
            batch_min=3, batch_max=12,
        ),
        # ── Stage 7: CMP Planarize (2 polishers) ──
        # 11. CMP A
        Rule(
            rule_id="cmp_a",
            consume={
                "wafer": Selector(conditions={"type": "deposited_wafer"}, num=1),
                "slurry": Selector(conditions={"type": "cmp_slurry", "grade": "oxide_cmp"}, num=1),
            },
            consume_batch={
                "polisher": Selector(conditions={"type": "cmp_polisher_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "cmp"}),
            },
            # re-entrant: coated_wafer pool
            produce={"planar": Selector(conditions={"type": "coated_wafer"}, num=1)},
            produce_batch={
                "polisher": Selector(conditions={"type": "cmp_polisher_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "cmp"}),
            },
            duration_s=240.0,
            duration_batch_s=480.0,  # pad conditioning
            batch_min=3, batch_max=6,
        ),
        # 12. CMP B
        Rule(
            rule_id="cmp_b",
            consume={
                "wafer": Selector(conditions={"type": "deposited_wafer"}, num=1),
                "slurry": Selector(conditions={"type": "cmp_slurry", "grade": "oxide_cmp"}, num=1),
            },
            consume_batch={
                "polisher": Selector(conditions={"type": "cmp_polisher_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "cmp"}),
            },
            produce={"planar": Selector(conditions={"type": "coated_wafer"}, num=1)},
            produce_batch={
                "polisher": Selector(conditions={"type": "cmp_polisher_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "cmp"}),
            },
            duration_s=240.0,
            duration_batch_s=480.0,
            batch_min=3, batch_max=6,
        ),
        # ── Stage 8: Metal deposition / back-end ──
        Rule(
            rule_id="metal_dep",
            consume={"wafer": Selector(conditions={"type": "coated_wafer"}, num=1)},
            consume_batch={
                "dep": Selector(conditions={"type": "cvd_deposition_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "deposition"}),
            },
            produce={"metal": Selector(conditions={"type": "deposited_wafer"}, num=1)},
            produce_batch={
                "dep": Selector(conditions={"type": "cvd_deposition_a", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "deposition"}),
            },
            duration_s=500.0,
            duration_batch_s=900.0,
            batch_min=3, batch_max=6,
        ),
        # ── Stage 9: Passivation (final oxide/nitride) ──
        Rule(
            rule_id="passivation",
            consume={"wafer": Selector(conditions={"type": "deposited_wafer"}, num=1)},
            consume_batch={
                "dep": Selector(conditions={"type": "cvd_deposition_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "deposition"}),
            },
            produce={"finished": Selector(conditions={"type": "finished_die"}, num=1)},
            produce_batch={
                "dep": Selector(conditions={"type": "cvd_deposition_b", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "deposition"}),
            },
            duration_s=350.0,
            duration_batch_s=600.0,
            batch_min=3, batch_max=12,
        ),
        # ── Stage 10: Wafer probe (sort) ──
        Rule(
            rule_id="wafer_probe",
            consume={"wafer": Selector(conditions={"type": "finished_die"}, num=1)},
            consume_batch={
                "prober": Selector(conditions={"type": "wafer_prober", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "test"}),
            },
            produce={"tested": Selector(conditions={"type": "finished_die"}, num=1)},
            produce_batch={
                "prober": Selector(conditions={"type": "wafer_prober", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "test"}),
            },
            duration_s=60.0,
            duration_batch_s=120.0,
            batch_min=1, batch_max=6,
        ),
        # ── Stage 11: Final test ──
        Rule(
            rule_id="final_test",
            consume={"die": Selector(conditions={"type": "finished_die"}, num=1)},
            consume_batch={
                "tester": Selector(conditions={"type": "final_tester", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "test"}),
            },
            produce={"packaged": Selector(conditions={"type": "packaged_chip"}, num=1)},
            produce_batch={
                "tester": Selector(conditions={"type": "final_tester", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "test"}),
            },
            duration_s=30.0,
            duration_batch_s=60.0,
            batch_min=1, batch_max=12,
        ),
        # ── Stage 12: Device test ──
        Rule(
            rule_id="device_test",
            consume={"chip": Selector(conditions={"type": "packaged_chip"}, num=1)},
            consume_batch={
                "tester": Selector(conditions={"type": "final_tester", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "test"}),
            },
            produce={"tested": Selector(conditions={"type": "tested_device"}, num=1)},
            produce_batch={
                "tester": Selector(conditions={"type": "final_tester", "state": "idle"}),
                "operator": Selector(conditions={"type": "operator", "cert": "test"}),
            },
            duration_s=60.0,
            duration_batch_s=120.0,
            batch_min=1, batch_max=12,
        ),
    ]

    # ── Orders ──────────────────────────────────────────────────────────
    orders: list[Order] = [
        Order(
            order_id="ORD-PMIC-001",
            consume={"product": Selector(conditions={"type": "tested_device"}, num=100)},
            deadline=_dt(days=35),
            late_delivery_penalty_per_s=20.0,
            early_delivery_bonus_per_s=5.0,
        ),
        Order(
            order_id="ORD-LOGIC-001",
            consume={"product": Selector(conditions={"type": "tested_device"}, num=60)},
            deadline=_dt(days=28),
            late_delivery_penalty_per_s=50.0,
        ),
        Order(
            order_id="ORD-PMIC-002",
            consume={"product": Selector(conditions={"type": "tested_device"}, num=80)},
            deadline=_dt(days=50),
            late_delivery_penalty_per_s=20.0,
        ),
        Order(
            order_id="ORD-LOGIC-002",
            consume={"product": Selector(conditions={"type": "tested_device"}, num=40)},
            deadline=_dt(days=45),
            late_delivery_penalty_per_s=30.0,
            early_delivery_bonus_per_s=8.0,
        ),
    ]

    return PlanningModel(
        entities=entities,
        rules=rules,
        orders=orders,
        holding_rules=holding_rules,
        objective=Objective(expression="$money_cent_remaining"),
        planning_start=PLANNING_START,
        planning_horizon_s=86400 * 90,
    )
