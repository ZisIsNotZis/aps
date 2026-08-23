package aps;

/** Problem fact: how many units of a type are needed (from orders). */
public class Demand {
    public String type;
    public long needed;

    public Demand() {}

    public Demand(String type, long needed) {
        this.type = type;
        this.needed = needed;
    }
}
