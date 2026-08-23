package aps;

public class BlockDef {
    public String ruleId;
    public int startTick;
    public int endTick;
    public int batchQty;
    public String equipmentId;

    public BlockDef() {}

    public BlockDef(String ruleId, int startTick, int endTick, int batchQty, String equipmentId) {
        this.ruleId = ruleId;
        this.startTick = startTick;
        this.endTick = endTick;
        this.batchQty = batchQty;
        this.equipmentId = equipmentId;
    }
}
