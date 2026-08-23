package aps;

public class OrderResult {
    public String orderId;
    public boolean fulfilled;
    public int latenessTicks;

    public OrderResult() {}

    public OrderResult(String orderId, boolean fulfilled, int latenessTicks) {
        this.orderId = orderId;
        this.fulfilled = fulfilled;
        this.latenessTicks = latenessTicks;
    }
}
