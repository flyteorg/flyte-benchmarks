# /// script
# requires-python = ">=3.12"
# dependencies = ["flytekit>=1.13"]
# ///
"""Reference solution (HELD OUT). Spec `etl_join`, Flyte v1 — filter/join/group."""
import json

from flytekit import task, workflow


@task
def filter_completed(orders: list[dict]) -> list[dict]:
    return [o for o in orders if o["status"] == "completed"]


@task
def join_region(orders: list[dict], customers: list[dict]) -> list[dict]:
    region_of = {c["customer_id"]: c["region"] for c in customers}
    out = []
    for o in orders:
        reg = region_of.get(o["customer_id"])
        if reg is not None:
            out.append({"region": reg, "amount_cents": o["amount_cents"]})
    return out


@task
def group_by_region(rows: list[dict]) -> list[dict]:
    agg: dict = {}
    for row in rows:
        a = agg.setdefault(row["region"], [0, 0])
        a[0] += 1
        a[1] += row["amount_cents"]
    return [{"region": r, "orders": c, "total_cents": t}
            for r, (c, t) in sorted(agg.items())]


@workflow
def wf(orders: list[dict], customers: list[dict]) -> list[dict]:
    kept = filter_completed(orders=orders)
    joined = join_region(orders=kept, customers=customers)
    return group_by_region(rows=joined)


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))
    print("TRIAL_OUTPUT_JSON:" + json.dumps({"by_region": wf(**inp)}))
