package aps;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ProblemInput {
    public List<RuleDef> rules;
    public List<OrderDef> orders;
    public Map<String, Integer> initialEntities;
    public int horizonTicks;
    public double timeLimitSeconds;
}
