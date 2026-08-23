package aps;

import ai.timefold.solver.core.api.domain.entity.PlanningEntity;
import ai.timefold.solver.core.api.domain.lookup.PlanningId;
import ai.timefold.solver.core.api.domain.variable.PlanningVariable;
import ai.timefold.solver.core.api.domain.variable.ShadowVariable;
import com.fasterxml.jackson.annotation.JsonIgnore;

@PlanningEntity
public class OperationAssignment {

    @PlanningId
    private String id;

    /** Which rule this operation executes. */
    private String ruleId;

    /** Which equipment this runs on. */
    private String equipmentId;

    /** Duration parameters (from the rule). */
    private int durationTicks;
    private int durationBatchTicks;
    private int batchMin;
    private int batchMax;
    private int horizon;
    /** BOM info: entity type this operation produces (for precedence constraints). */
    private String producesType;
    /** BOM info: entity type this operation consumes (for precedence constraints). */
    private String consumesType;

    // ── Planning variables ──────────────────────────────────────────────

    private Long startTick;
    private Integer batchQty;

    // ── Shadow variable: derived from start + duration ──────────────────

    private Long endTick;

    public OperationAssignment() {}

    public OperationAssignment(String id, String ruleId, String equipmentId,
                                int durationTicks, int durationBatchTicks,
                                int batchMin, int batchMax, int horizon,
                                String producesType, String consumesType) {
        this.id = id;
        this.ruleId = ruleId;
        this.equipmentId = equipmentId;
        this.durationTicks = durationTicks;
        this.durationBatchTicks = durationBatchTicks;
        this.batchMin = batchMin;
        this.batchMax = batchMax;
        this.horizon = horizon;
        this.producesType = producesType;
        this.consumesType = consumesType;
    }

    @PlanningVariable(valueRangeProviderRefs = {"tickRange"})
    public Long getStartTick() { return startTick; }
    public void setStartTick(Long startTick) { this.startTick = startTick; }

    @PlanningVariable(valueRangeProviderRefs = {"batchRange"})
    public Integer getBatchQty() { return batchQty; }
    public void setBatchQty(Integer batchQty) { this.batchQty = batchQty; }

    /** Convenience for Timefold's sum() collector which needs long-returning getter. */
    public long getBatchQtyLong() { return batchQty != null ? batchQty.longValue() : 0L; }

    public Long getEndTick() { return endTick; }
    public void setEndTick(Long endTick) { this.endTick = endTick; }

    // ── Safe accessors for constraint stream joiners ────────────────────

    /** Returns startTick, or 0 if null (safe for constraints). */
    public long getStartTickSafe() {
        return startTick != null ? startTick : 0L;
    }

    /** Returns endTick (start + duration), or 0 if null. */
    public long getEndTickSafe() {
        if (startTick == null || batchQty == null) return 0L;
        return startTick + (long) durationBatchTicks + (long) batchQty * (long) durationTicks;
    }

    public long computeDuration() {
        return (long) durationBatchTicks + (batchQty != null ? (long) batchQty * (long) durationTicks : 0L);
    }

    // Getters/setters for problem facts
    public String getRuleId() { return ruleId; }
    public void setRuleId(String ruleId) { this.ruleId = ruleId; }
    public String getEquipmentId() { return equipmentId; }
    public void setEquipmentId(String equipmentId) { this.equipmentId = equipmentId; }
    public int getDurationTicks() { return durationTicks; }
    public int getDurationBatchTicks() { return durationBatchTicks; }
    public int getBatchMin() { return batchMin; }
    public int getBatchMax() { return batchMax; }
    public int getHorizon() { return horizon; }
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getProducesType() { return producesType; }
    public String getConsumesType() { return consumesType; }
}
