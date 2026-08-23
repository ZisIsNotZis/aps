package aps;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class OrderDef {
    public String orderId;
    public String type;
    public int needed;
    public Integer deadlineTicks;
    public double latePenaltyPerTick;
}
