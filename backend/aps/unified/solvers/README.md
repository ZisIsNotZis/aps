# Solver Backends

APS supports multiple solver backends via a plugin architecture. All solvers implement the same contract: `solve(CompiledPlan, SolverConfig) -> SolverResult`.

## Available Solvers

| Solver | Type | Status | Default |
|--------|------|--------|---------|
| `greedy` | Heuristic list scheduling | Production | No |
| `cp_sat` | OR-Tools CP-SAT | Production | **Yes** |
| `gurobi` | Gurobi MIP | Available | No |
| `timefold` | Timefold (Java sidecar) | Experimental | No |

## 5-Minute Benchmark (2026-07-29)

Each solver was given 300s per scenario. Intermediate solution quality was recorded for decay curve visualization.

### Schedule Quality

| Scenario | cp_sat (blk/mk) | gurobi (blk/mk) | timefold (blk/mk) |
|---|---|---|---|
| discrete | **1/360s** *optimal* | 1/360s *optimal* | 10/1200s |
| electronics | **57/3660s** *4/4 orders* | license limit | 590/284460s *3/4 orders* |
| job_shop | **8/420s** *optimal* | 10/420s *optimal* | 160/8880s |
| pharma | **21/10200s** | 22/10200s | 160/290160s *1/3 orders* |

### Decay Curve Highlights

**CP-SAT** (electronics_smt, 101 intermediate solutions):
- First solution at 0.4s: obj=77,400
- Improved continuously: 0.9s→161, 5.8s→139, 31.6s→92, 80s→72, 246s→**61**
- Best bound: 10 (nearly optimal)

**Gurobi** (pharma, 19 intermediate solutions):
- All improvements found within 4.4s: obj dropped from 435,000 → **170**
- Remaining 296s: no further improvement found
- Bound improved from 0 → 45

**Timefold** (pharma, 12,077 intermediate solutions):
- Dense sampling but score not correlated with schedule quality
- Reward calibration needed to align soft score with makespan

### Overall

| Solver | Solve time (4 scenarios) | Quality | Notes |
|--------|--------------------------|---------|-------|
| cp_sat | 0.02–300.6s | **Best** | 100% fulfillment on all benchmarked scenarios |
| gurobi | 0.00–300.0s | Matches cp_sat | Free license limits to 3/4 scenarios |
| timefold | 301.6–312.5s | Poor | JVM startup + 300s solve; 3/4 orders on electronics, 1/3 on pharma |

**Verdict: CP-SAT is the default production solver.** Gurobi matches it where the free license allows. Timefold needs material flow constraints and reward calibration to be competitive.

### Decay Curve Data

The benchmark results (including full decay curves) are saved at `docs/solver_benchmark_5min.json`. Each solver entry includes:

- `metrics`: Final schedule quality (blocks, makespan, fulfilled orders)
- `solution_curve`: Array of `{time_s, objective_value, best_bound}` (CP-SAT/Gurobi) or `{timeS, score}` (Timefold) for each intermediate solution found

To visualize the decay curves:

```python
import json
with open("docs/solver_benchmark_5min.json") as f:
    data = json.load(f)
curve = data["results"]["electronics_smt"]["cp_sat"]["solution_curve"]
times = [p["time_s"] for p in curve]
objs = [p["objective_value"] for p in curve]
# Plot with matplotlib
```

## Future Work (Deferred)

### 1. Timefold Demand Fulfillment

The Timefold constraint stream API has type inference issues with `groupBy` + `sumLong` + `join` pipelines needed for demand/material balance constraints. The underlying Java code in `ScheduleConstraints.java` compiles with BOM precedence and no-overlap, but the demand fulfillment constraint requires a `groupBy` collector chain that the Java compiler cannot infer.

**Fix approach**: Use local variable type hints or extract the `groupBy` result into an intermediate `BiConstraintStream` variable before joining with `Demand`:

```java
var productionByType = cf.forEach(OperationAssignment.class)
    .filter(op -> op.getBatchQty() != null && op.getBatchQty() > 0 && op.getProducesType() != null)
    .groupBy(OperationAssignment::getProducesType, 
             sumLong(OperationAssignment::getBatchQtyLong));
var demandFulfillment = productionByType
    .join(cf.from(Demand.class))
    .filter((type, totalQty, demand) -> type.equals(demand.type))
    .filter((type, totalQty, demand) -> totalQty < demand.needed)
    .penalizeLong(HardSoftLongScore.ONE_HARD, ...);
```

### 2. Production Reward Weight Calibration

The current Timefold per-operation reward of 1M is a guess. The optimal reward should be calibrated to balance against the makespan penalty. The reward should be `max_possible_makespan + 1` per operation, so that activating one operation is always better than idling, but activating a second operation is only better if it doesn't increase makespan proportionally.

### 3. JVM Warm-up

Timefold incurs ~5-15s JVM startup overhead per solve. This should be moved to import time (warm the JVM when the module loads, not when the user clicks "solve"). The `timefold.py` plugin currently runs the JAR fresh each solve.

**Fix**: Keep a persistent JVM subprocess that reads problem JSON from stdin and writes solution JSON to stdout. Pipe requests to it. This amortizes the JVM startup across multiple solves.

### 4. Gurobi Commercial License

The free Gurobi license limits model size (~2000 variables), which blocks electronics, automotive, food, and semiconductor scenarios. A commercial license removes this limit and Gurobi would likely match or beat CP-SAT on all scenarios.

### 5. optapy (OptaPlanner) — Not Integrated

OptaPlanner (via `optapy`) was installed and tested but is unmaintained (Red Hat dropped it). Timefold is the active fork. The Python optapy package wraps an old OptaPlanner version and is not recommended for new development.

### 6. LocalSolver — Not Available

LocalSolver is a commercial-only product not available on PyPI. Not integrated.

## Adding a New Solver

1. Create `solvers/my_solver.py`
2. Register: `_SOLVERS["my_solver"] = solve_fn`
3. Follow the signature: `solve_fn(plan: CompiledPlan, config: SolverConfig) -> SolverResult`
4. Import in `_solve.py` to trigger registration
5. Use: `SolverConfig(solver="my_solver")`