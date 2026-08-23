package aps;

import ai.timefold.solver.core.api.domain.solution.PlanningEntityCollectionProperty;
import ai.timefold.solver.core.api.domain.solution.PlanningScore;
import ai.timefold.solver.core.api.domain.solution.PlanningSolution;
import ai.timefold.solver.core.api.domain.solution.ProblemFactCollectionProperty;
import ai.timefold.solver.core.api.domain.valuerange.ValueRangeProvider;
import ai.timefold.solver.core.api.score.buildin.hardsoftlong.HardSoftLongScore;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.IntStream;

@PlanningSolution
public class ScheduleSolution {

    private List<OperationAssignment> operations;
    private List<Demand> demands;
    private HardSoftLongScore score;
    private ProblemInput problem;

    public ScheduleSolution() {
        this.operations = new ArrayList<>();
        this.demands = new ArrayList<>();
    }

    public ScheduleSolution(List<OperationAssignment> operations, List<Demand> demands, ProblemInput problem) {
        this.operations = operations;
        this.demands = demands;
        this.problem = problem;
    }

    @PlanningEntityCollectionProperty
    public List<OperationAssignment> getOperations() { return operations; }
    public void setOperations(List<OperationAssignment> operations) { this.operations = operations; }

    @ProblemFactCollectionProperty
    public List<Demand> getDemands() { return demands; }
    public void setDemands(List<Demand> demands) { this.demands = demands; }

    @PlanningScore
    public HardSoftLongScore getScore() { return score; }
    public void setScore(HardSoftLongScore score) { this.score = score; }

    @ProblemFactCollectionProperty
    @ValueRangeProvider(id = "tickRange")
    public List<Long> getTickRange() {
        int h = problem != null ? problem.horizonTicks : 10000;
        List<Long> range = new ArrayList<>();
        for (long i = 0; i <= h; i++) range.add(i);
        return range;
    }

    @ValueRangeProvider(id = "batchRange")
    public List<Integer> getBatchRange() {
        List<Integer> range = new ArrayList<>();
        for (int i = 0; i <= 100; i++) range.add(i);
        return range;
    }

    public ProblemInput getProblem() { return problem; }
    public void setProblem(ProblemInput problem) { this.problem = problem; }
}
