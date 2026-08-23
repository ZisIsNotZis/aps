package aps;

import ai.timefold.solver.core.api.score.buildin.hardsoftlong.HardSoftLongScore;
import ai.timefold.solver.core.api.score.stream.Constraint;
import ai.timefold.solver.core.api.score.stream.ConstraintFactory;
import ai.timefold.solver.core.api.score.stream.ConstraintProvider;
import ai.timefold.solver.core.api.score.stream.Joiners;

/** Timefold constraints: no-overlap, BOM precedence, batch limits, makespan, production reward. */
public class ScheduleConstraints implements ConstraintProvider {

    @Override
    public Constraint[] defineConstraints(ConstraintFactory cf) {
        return new Constraint[] {
            equipmentNoOverlap(cf),
            bomPrecedence(cf),
            batchLimits(cf),
            startWithinHorizon(cf),
            makespanPenalty(cf),
            productionReward(cf),
        };
    }

    Constraint equipmentNoOverlap(ConstraintFactory cf) {
        return cf.forEachUniquePair(OperationAssignment.class,
                Joiners.equal(OperationAssignment::getEquipmentId),
                Joiners.overlapping(
                    OperationAssignment::getStartTickSafe,
                    OperationAssignment::getEndTickSafe,
                    OperationAssignment::getStartTickSafe,
                    OperationAssignment::getEndTickSafe))
            .penalize(HardSoftLongScore.ONE_HARD)
            .asConstraint("Equipment no-overlap");
    }

    /** Hard: if op1 produces a type that op2 consumes, op1 must finish before op2 starts. */
    Constraint bomPrecedence(ConstraintFactory cf) {
        return cf.forEach(OperationAssignment.class)
            .filter(op -> op.getProducesType() != null)
            .join(OperationAssignment.class,
                  Joiners.equal(OperationAssignment::getProducesType,
                                OperationAssignment::getConsumesType))
            .filter((producer, consumer) ->
                producer.getEndTickSafe() > consumer.getStartTickSafe())
            .penalize(HardSoftLongScore.ONE_HARD)
            .asConstraint("BOM precedence");
    }

    Constraint batchLimits(ConstraintFactory cf) {
        return cf.forEach(OperationAssignment.class)
            .filter(op -> op.getBatchQty() != null && op.getBatchQty() > 0)
            .filter(op -> op.getBatchQty() < op.getBatchMin() || op.getBatchQty() > op.getBatchMax())
            .penalize(HardSoftLongScore.ONE_HARD)
            .asConstraint("Batch limits");
    }

    Constraint startWithinHorizon(ConstraintFactory cf) {
        return cf.forEach(OperationAssignment.class)
            .filter(op -> op.getStartTick() != null && op.getStartTick() > op.getHorizon())
            .penalize(HardSoftLongScore.ONE_HARD)
            .asConstraint("Horizon");
    }

    /** Soft: minimize makespan by penalizing active operations' end ticks. */
    Constraint makespanPenalty(ConstraintFactory cf) {
        return cf.forEach(OperationAssignment.class)
            .filter(op -> op.getBatchQty() != null && op.getBatchQty() >= op.getBatchMin())
            .penalizeLong(HardSoftLongScore.ONE_SOFT, OperationAssignment::getEndTickSafe)
            .asConstraint("Makespan");
    }

    /** Soft: reward active operations. Large weight to overcome makespan penalty. */
    Constraint productionReward(ConstraintFactory cf) {
        return cf.forEach(OperationAssignment.class)
            .filter(op -> op.getBatchQty() != null && op.getBatchQty() >= op.getBatchMin())
            .rewardLong(HardSoftLongScore.ONE_SOFT,
                op -> 1_000_000L)
            .asConstraint("Production reward");
    }
}