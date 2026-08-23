import argparse
import random
import time

from main import PlanningInput, plan_advanced_schedule


def _weekly_slots(rng: random.Random) -> list[dict]:
    slots = []
    for d in range(7):
        if rng.random() < 0.15:
            continue
        if rng.random() < 0.2:
            slots.append({"day_of_week": d, "start_hour": 0, "end_hour": 8})
            slots.append({"day_of_week": d, "start_hour": 10, "end_hour": 24})
        else:
            slots.append({"day_of_week": d, "start_hour": 0, "end_hour": 24})
    if not slots:
        slots.append({"day_of_week": 0, "start_hour": 0, "end_hour": 24})
    return slots


def make_mock_payload(
    seed: int,
    equipment_count: int,
    worker_count: int,
    product_count: int = 24,
    order_count: int = 48,
) -> PlanningInput:
    rng = random.Random(seed)
    tasks = [f"task_{i}" for i in range(12)]
    resources = [
        {
            "code": "electricity",
            "name": "Electricity",
            "price_per_hour": 14.0,
            "hourly_prices": [
                {"start_hour": 0, "end_hour": 6, "price_per_hour": 9.2},
                {"start_hour": 6, "end_hour": 18, "price_per_hour": 18.5},
                {"start_hour": 18, "end_hour": 24, "price_per_hour": 12.8},
            ],
        },
        {
            "code": "water",
            "name": "Water",
            "price_per_hour": 4.5,
            "hourly_prices": [
                {"start_hour": 0, "end_hour": 8, "price_per_hour": 3.6},
                {"start_hour": 8, "end_hour": 20, "price_per_hour": 5.0},
                {"start_hour": 20, "end_hour": 24, "price_per_hour": 3.9},
            ],
        },
        {
            "code": "gas",
            "name": "Industrial Gas",
            "price_per_hour": 9.0,
            "hourly_prices": [
                {"start_hour": 0, "end_hour": 7, "price_per_hour": 7.5},
                {"start_hour": 7, "end_hour": 19, "price_per_hour": 10.4},
                {"start_hour": 19, "end_hour": 24, "price_per_hour": 8.3},
            ],
        },
        {
            "code": "coolant",
            "name": "Coolant",
            "price_per_hour": 6.8,
            "hourly_prices": [
                {"start_hour": 0, "end_hour": 24, "price_per_hour": 6.8},
            ],
        },
    ]

    equipments = []
    for i in range(equipment_count):
        capable = rng.sample(tasks, k=rng.randint(3, 6))
        eff = {t: round(rng.uniform(0.5, 1.6), 3) for t in capable}
        usage = {}
        for t in capable:
            usage[t] = {
                "electricity": round(rng.uniform(0.4, 1.4), 3),
                "water": round(rng.uniform(0.0, 0.5), 3),
                "gas": round(rng.uniform(0.0, 0.8), 3),
                "coolant": round(rng.uniform(0.0, 0.6), 3),
            }
        equipments.append(
            {
                "code": f"EQ-{i:03d}",
                "name": f"Equipment {i:03d}",
                "efficiencies": eff,
                "resource_usage_per_hour": usage,
                "idle_cost_per_hour": round(rng.uniform(1.5, 8), 2),
                "power_on_time_hour": round(rng.uniform(0.05, 0.4), 2),
                "power_off_time_hour": round(rng.uniform(0.05, 0.4), 2),
                "availability": _weekly_slots(rng),
            }
        )

    workers = []
    for i in range(worker_count):
        capable = rng.sample(tasks, k=rng.randint(3, 7))
        skills = {t: round(rng.uniform(0.82, 1.2), 3) for t in capable}
        workers.append(
            {
                "code": f"WK-{i:03d}",
                "name": f"Worker {i:03d}",
                "skills": skills,
                "work_cost_per_hour": round(rng.uniform(12, 48), 2),
                "idle_cost_per_hour": round(rng.uniform(1, 8), 2),
                "commute_in_time_hour": round(rng.uniform(0.0, 0.3), 2),
                "commute_out_time_hour": round(rng.uniform(0.0, 0.3), 2),
                "availability": _weekly_slots(rng),
            }
        )

    products = []
    for i in range(product_count):
        workflow = []
        for s in range(rng.randint(3, 6)):
            workflow.append(
                {
                    "id": f"p{i}-s{s}",
                    "task_type": rng.choice(tasks),
                    "base_duration": round(rng.uniform(0.6, 3.2), 2),
                    "assemble_components": [],
                }
            )
        products.append({"code": f"P-{i:03d}", "name": f"Product {i:03d}", "workflow": workflow})

    orders = []
    for i in range(order_count):
        line_count = rng.randint(1, 3)
        lines = []
        for _ in range(line_count):
            lines.append({"product": f"P-{rng.randint(0, product_count - 1):03d}", "quantity": rng.randint(1, 4)})
        orders.append(
            {
                "id": f"O-{i:04d}",
                "deadline_hour": float(rng.randint(120, 720)),
                "penalty_per_hour": round(rng.uniform(15, 220), 2),
                "pre_deadline_bonus_per_hour": round(rng.uniform(0, 36), 2),
                "lines": lines,
            }
        )

    return PlanningInput(resources=resources, equipments=equipments, workers=workers, products=products, orders=orders)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scale benchmark for APS planner.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--equipments", type=int, default=100)
    parser.add_argument("--workers", type=int, default=100)
    parser.add_argument("--products", type=int, default=24)
    parser.add_argument("--orders", type=int, default=48)
    args = parser.parse_args()

    payload = make_mock_payload(
        seed=args.seed,
        equipment_count=args.equipments,
        worker_count=args.workers,
        product_count=args.products,
        order_count=args.orders,
    )
    total_ops = sum(
        len(product.workflow) * line.quantity
        for order in payload.orders
        for line in order.lines
        for product in payload.products
        if product.code == line.product
    )
    print(
        f"Benchmark payload: eq={args.equipments}, workers={args.workers}, products={args.products}, "
        f"orders={args.orders}, approx_ops={total_ops}"
    )
    t0 = time.perf_counter()
    result = plan_advanced_schedule(payload)
    elapsed = time.perf_counter() - t0
    print(
        f"Elapsed: {elapsed:.2f}s | ops={result.total_operations} unscheduled={result.unscheduled_operations} "
        f"makespan(min)={result.makespan:.1f} total_cost={result.total_cost:.2f}"
    )


if __name__ == "__main__":
    main()
