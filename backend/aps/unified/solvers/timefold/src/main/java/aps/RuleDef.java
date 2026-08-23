package aps;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class RuleDef {
    public String ruleId;
    public int batchMin;
    public int batchMax;
    public int durationTicks;
    public int durationBatchTicks;
    public String equipmentType;
    public Map<String, Integer> consume;
    public Map<String, Integer> produce;
}
