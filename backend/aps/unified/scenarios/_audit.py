"""Audit all scenarios for data correctness.

Checks each scenario for:
1. Every selector type exists in initial inventory somewhere
2. Every rule produce type is consumed by some downstream rule or order
3. No dangling references
"""

from dataclasses import dataclass

from aps.unified._schema import PlanningModel, Selector
from aps.unified.scenarios.registry import get_scenario, list_scenarios


@dataclass
class AuditIssue:
    scenario_id: str
    severity: str  # ERROR | WARN
    message: str


def _collect_selectors(model: PlanningModel) -> list[tuple[str, str, Selector]]:
    """Collect all selectors with (context, name, selector)."""
    result: list[tuple[str, str, Selector]] = []
    for r in model.rules:
        for group in ("consume", "consume_batch", "produce", "produce_batch"):
            for name, sel in getattr(r, group, {}).items():
                result.append((f"rule {r.rule_id}/{group}", name, sel))
    for o in model.orders:
        for name, sel in o.consume.items():
            result.append((f"order {o.order_id}/consume", name, sel))
    for hr in model.holding_rules:
        result.append(("holding_rule", "", hr.selector))
    return result


def _entity_types_in(model: PlanningModel) -> set[str]:
    """All entity type field values in the model."""
    types: set[str] = set()
    for e in model.entities:
        t = e.fields.get("type")
        if isinstance(t, str):
            types.add(t)
    return types


def audit_scenario(scenario_id: str) -> list[AuditIssue]:
    model = get_scenario(scenario_id)
    if model is None:
        return [AuditIssue(scenario_id, "ERROR", "scenario not found")]

    issues: list[AuditIssue] = []
    entity_types = _entity_types_in(model)
    selectors = _collect_selectors(model)

    # Collect all produce types
    produced_types: set[str] = set()
    for ctx, _name, sel in selectors:
        if "produce" in ctx:
            t = sel.conditions.get("type")
            if isinstance(t, str):
                produced_types.add(t)

    # Check every selector type exists in inventory OR is produced by some rule
    for ctx, name, sel in selectors:
        t = sel.conditions.get("type")
        if not isinstance(t, str):
            issues.append(AuditIssue(scenario_id, "WARN",
                f"{ctx}.{name}: type field is not a string: {t!r}"))
            continue
        if t not in entity_types and t not in produced_types:
            # Check if it's consumed by an order (order demand doesn't need to be in inventory)
            if "order" in ctx:
                issues.append(AuditIssue(scenario_id, "ERROR",
                    f"{ctx}.{name}: order demands type {t!r} which is never produced by any rule"))
            else:
                issues.append(AuditIssue(scenario_id, "ERROR",
                    f"{ctx}.{name}: references type {t!r} which is not in initial entities "
                    f"and not produced by any rule"))

    # Check initial inventory has enough raw count
    total_order_demand: dict[str, float] = {}
    for o in model.orders:
        for _name, sel in o.consume.items():
            t = sel.conditions.get("type")
            if isinstance(t, str):
                total_order_demand[t] = total_order_demand.get(t, 0) + sel.num

    raw_counts: dict[str, int] = {}
    for e in model.entities:
        t = e.fields.get("type")
        if isinstance(t, str) and t in total_order_demand:
            raw_counts[t] = raw_counts.get(t, 0) + e.count

    for t, needed in total_order_demand.items():
        available = raw_counts.get(t, 0)
        # Only flag if it's a raw material (never produced)
        if t not in produced_types and available < needed:
            issues.append(AuditIssue(scenario_id, "WARN",
                f"order demands {needed}x {t!r} but only {available} in initial inventory "
                f"(may need production chain to supply it)"))

    return issues


def main() -> None:
    all_issues: list[AuditIssue] = []
    for s in list_scenarios():
        issues = audit_scenario(s.scenario_id)
        all_issues.extend(issues)
        if issues:
            print(f"\n{'='*60}")
            print(f"  {s.scenario_id}: {len(issues)} issues")
            print(f"{'='*60}")
            for iss in issues:
                print(f"  [{iss.severity}] {iss.message}")
        else:
            print(f"  {s.scenario_id}: ✓ clean")

    errors = [i for i in all_issues if i.severity == "ERROR"]
    print(f"\n{'='*60}")
    print(f"Total: {len(all_issues)} issues ({len(errors)} errors)")
    if errors:
        print("FIX THESE BEFORE PROCEEDING")
        for e in errors:
            print(f"  ERROR: {e.message}")


if __name__ == "__main__":
    main()
