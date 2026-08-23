package aps;

import java.util.List;

public class SolutionOutput {
    public List<BlockDef> blocks;
    public List<OrderResult> orderResults;
    public int makespanTicks;
    public double solverTimeSeconds;
    public String status;
    public List<CurvePoint> solutionCurve;

    public SolutionOutput() {}

    public SolutionOutput(List<BlockDef> blocks, List<OrderResult> orderResults,
                          int makespanTicks, double solverTimeSeconds, String status,
                          List<CurvePoint> solutionCurve) {
        this.blocks = blocks;
        this.orderResults = orderResults;
        this.makespanTicks = makespanTicks;
        this.solverTimeSeconds = solverTimeSeconds;
        this.status = status;
        this.solutionCurve = solutionCurve;
    }

    public static class CurvePoint {
        public double timeS;
        public long score;
        public CurvePoint() {}
        public CurvePoint(double timeS, long score) {
            this.timeS = timeS;
            this.score = score;
        }
    }
}
