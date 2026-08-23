package aps;

import ai.timefold.solver.core.api.score.buildin.hardsoftlong.HardSoftLongScore;
import ai.timefold.solver.core.api.solver.Solver;
import ai.timefold.solver.core.api.solver.SolverFactory;
import ai.timefold.solver.core.api.solver.event.SolverEventListener;
import ai.timefold.solver.core.config.solver.SolverConfig;
import ai.timefold.solver.core.config.solver.termination.TerminationConfig;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import java.io.File;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;

/** Timefold solver entry point. Usage:
 *  java aps.Solve problem.json solution.json [timeLimitSeconds]
 *
 *  Reads problem from JSON, solves, writes solution to JSON. */
public class Solve {

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("Usage: Solve <problem.json> <solution.json> [timeLimitSeconds]");
            System.exit(1);
        }
        ObjectMapper mapper = new ObjectMapper();
        mapper.enable(SerializationFeature.INDENT_OUTPUT);

        // ── Read problem ────────────────────────────────────────────────
        ProblemInput problem = mapper.readValue(new File(args[0]), ProblemInput.class);
        double timeLimit = args.length > 2 ? Double.parseDouble(args[2]) : 30.0;

        // ── Build planning entities ─────────────────────────────────────
        Map<String, List<RuleDef>> rulesByEquipment = new HashMap<>();
        for (RuleDef rule : problem.rules) {
            String eqType = rule.equipmentType;
            rulesByEquipment.computeIfAbsent(eqType, k -> new ArrayList<>()).add(rule);
        }

        List<OperationAssignment> operations = new ArrayList<>();
        int opId = 0;
        int maxSlots = 10;
        for (Map.Entry<String, Integer> entry : problem.initialEntities.entrySet()) {
            String eqType = entry.getKey();
            int count = entry.getValue();
            // This is simplified: we need equipment entity IDs, not just types.
            // We create slots for each equipment entity of each type.
            for (int e = 0; e < count; e++) {
                String eqId = eqType + "_" + e;
                List<RuleDef> eqRules = rulesByEquipment.getOrDefault(eqType, List.of());
                if (eqRules.isEmpty()) continue;

                for (RuleDef rule : eqRules) {
                    // Extract BOM info: first produce type and first consume type
                    String prodType = (rule.produce != null && !rule.produce.isEmpty())
                        ? rule.produce.keySet().iterator().next() : null;
                    String consType = (rule.consume != null && !rule.consume.isEmpty())
                        ? rule.consume.keySet().iterator().next() : null;
                    for (int s = 0; s < maxSlots; s++) {
                        OperationAssignment op = new OperationAssignment(
                            "op_" + opId++, rule.ruleId, eqId,
                            rule.durationTicks, rule.durationBatchTicks,
                            rule.batchMin, rule.batchMax, problem.horizonTicks,
                            prodType, consType
                        );
                        // Initialize with random values
                        op.setStartTick((long) (Math.random() * problem.horizonTicks));
                        op.setBatchQty(rule.batchMin + (int)(Math.random() * (rule.batchMax - rule.batchMin + 1)));
                        operations.add(op);
                    }
                }
            }
        }

        // ── Configure solver (programmatic, no XML needed) ──────────────
        SolverConfig config = new SolverConfig()
            .withSolutionClass(ScheduleSolution.class)
            .withEntityClasses(OperationAssignment.class)
            .withConstraintProviderClass(ScheduleConstraints.class)
            .withTerminationConfig(new TerminationConfig()
                .withSecondsSpentLimit((long) Math.ceil(timeLimit)));

        SolverFactory<ScheduleSolution> factory = SolverFactory.create(config);
        Solver<ScheduleSolution> solver = factory.buildSolver();

        // ── Build demands (what each order needs) ───────────────────────
        List<Demand> demands = new ArrayList<>();
        for (OrderDef order : problem.orders) {
            demands.add(new Demand(order.type, order.needed));
        }

        // ── Solve ───────────────────────────────────────────────────────
        ScheduleSolution solution = new ScheduleSolution(operations, demands, problem);
        long startTime = System.currentTimeMillis();

        // Record best solution changes for decay curve
        List<SolutionOutput.CurvePoint> curve = new CopyOnWriteArrayList<>();
        solver.addEventListener(event -> {
            double elapsed = event.getTimeMillisSpent() / 1000.0;
            HardSoftLongScore s = (HardSoftLongScore) event.getNewBestScore();
            curve.add(new SolutionOutput.CurvePoint(elapsed, s != null ? s.getSoftScore() : 0));
        });

        solution = solver.solve(solution);
        double elapsed = (System.currentTimeMillis() - startTime) / 1000.0;

        // ── Extract solution ────────────────────────────────────────────
        List<BlockDef> blocks = new ArrayList<>();
        HardSoftLongScore score = (HardSoftLongScore) solution.getScore();
        boolean isFeasible = score != null && !score.isFeasible();

        // Only extract blocks that are actually active (batchQty > 0)
        for (OperationAssignment op : solution.getOperations()) {
            if (op.getBatchQty() != null && op.getBatchQty() > 0) {
                blocks.add(new BlockDef(
                    op.getRuleId(),
                    op.getStartTick().intValue(),
                    (int) op.getEndTickSafe(),
                    op.getBatchQty(),
                    op.getEquipmentId()
                ));
            }
        }

        // ── Write output ────────────────────────────────────────────────
        String status = (score != null && score.isFeasible()) ? "feasible" :
                        (score != null && !score.isFeasible()) ? "infeasible" : "timeout";
        if (blocks.isEmpty()) status = "timeout";

        int maxEnd = blocks.stream().mapToInt(b -> b.endTick).max().orElse(0);
        List<OrderResult> orderResults = new ArrayList<>();
        for (OrderDef order : problem.orders) {
            orderResults.add(new OrderResult(order.orderId, false, 0));
        }

        SolutionOutput output = new SolutionOutput(blocks, orderResults, maxEnd, elapsed, status, curve);
        mapper.writeValue(new File(args[1]), output);
    }
}
