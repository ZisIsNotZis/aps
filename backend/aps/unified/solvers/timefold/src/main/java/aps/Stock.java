package aps;

/** Problem fact: initial inventory of a material type. */
public class Stock {
    public String type;
    public long initialCount;

    public Stock() {}

    public Stock(String type, long initialCount) {
        this.type = type;
        this.initialCount = initialCount;
    }
}