"""Benchmark all solvers across all scenarios."""
import time
from aps.unified._compile import compile_model
from aps.unified._solve import solve
from aps.unified.solvers import SolverConfig
from aps.unified.scenarios.registry import list_scenarios, get_scenario

scenarios = list_scenarios()
print(f"Found {len(scenarios)} scenarios")
for s in scenarios:
    print(f"  {s.scenario_id}: {s.name}")
print()

results = {}

for sc in scenarios:
    sid = sc.scenario_id
    print(f"═══ {sid} ═══")
    model = get_scenario(sid)
    if model is None:
        print("  SKIP — not found")
        continue
    compiled = compile_model(model)
    print(f"  entities={len(model.entities)} rules={len(model.rules)} orders={len(model.orders)} horizon={compiled.horizon_ticks} ticks")

    for solver_name in ["greedy", "cp_sat", "pytorch", "fluid"]:
        try:
            t0 = time.monotonic()
            result = solve(compiled, SolverConfig(solver=solver_name, time_limit_s=30.0))
            dt = time.monotonic() - t0
            fulfilled = sum(1 for o in result.order_outcomes if o.fulfilled)
            total_orders = len(result.order_outcomes)
            n_blocks = len(result.scheduled_blocks)
            makespan = result.makespan_s
            status = result.status
            print(f"  {solver_name:>8}: {n_blocks:>4} blocks, {fulfilled}/{total_orders} orders, makespan={makespan:>8}s, time={dt:>7.2f}s, status={status}")
            results.setdefault(sid, {})[solver_name] = {
                "blocks": n_blocks, "fulfilled": fulfilled, "total_orders": total_orders,
                "makespan_s": makespan, "time_s": round(dt, 2), "status": status,
            }
        except Exception as e:
            print(f"  {solver_name:>8}: ERROR — {e}")

print()
print("=" * 90)
print("SUMMARY TABLE")
print("=" * 90)
header = f"{'Scenario':<30} {'Metric':>10} {'Greedy':>10} {'CP-SAT':>10} {'PyTorch':>10}"
print(header)
print("-" * 90)

for sid in sorted(results):
    r = results[sid]
    g = r.get("greedy", {})
    c = r.get("cp_sat", {})
    p = r.get("pytorch", {})

    g_ord = f"{g.get('fulfilled', '?')}/{g.get('total_orders', '?')}"
    c_ord = f"{c.get('fulfilled', '?')}/{c.get('total_orders', '?')}"
    p_ord = f"{p.get('fulfilled', '?')}/{p.get('total_orders', '?')}"

    print(f"{sid:<30} {'blocks':>10} {str(g.get('blocks', '—')):>10} {str(c.get('blocks', '—')):>10} {str(p.get('blocks', '—')):>10}")
    print(f"{'':<30} {'orders':>10} {g_ord:>10} {c_ord:>10} {p_ord:>10}")
    print(f"{'':<30} {'makespan':>10} {str(g.get('makespan_s', '—')):>10} {str(c.get('makespan_s', '—')):>10} {str(p.get('makespan_s', '—')):>10}")
    print(f"{'':<30} {'time_s':>10} {str(g.get('time_s', '—')):>10} {str(c.get('time_s', '—')):>10} {str(p.get('time_s', '—')):>10}")
    print()

# Winner counts
winners = {"blocks": {}, "orders": {}, "speed": {}}
for sid in sorted(results):
    r = results[sid]
    # Most orders fulfilled
    best_ord = max(r.keys(), key=lambda s: r[s].get("fulfilled", 0))
    winners["orders"][best_ord] = winners["orders"].get(best_ord, 0) + 1
    # Most blocks
    best_blk = max(r.keys(), key=lambda s: r[s].get("blocks", 0))
    winners["blocks"][best_blk] = winners["blocks"].get(best_blk, 0) + 1
    # Fastest
    best_spd = min(r.keys(), key=lambda s: r[s].get("time_s", 9999))
    winners["speed"][best_spd] = winners["speed"].get(best_spd, 0) + 1

print("=" * 90)
print("WINNER COUNTS (scenarios won)")
print("=" * 90)
for category, counts in winners.items():
    print(f"  {category}: {', '.join(f'{s}: {c}' for s, c in sorted(counts.items()))}")