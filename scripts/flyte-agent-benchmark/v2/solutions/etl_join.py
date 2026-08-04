# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
"""Reference solution (HELD OUT). Spec `etl_join`, Flyte v2 — filter/join/group."""
import json

import flyte

env = flyte.TaskEnvironment(name="etl_join")


@env.task
async def filter_completed(orders: list[dict]) -> list[dict]:
    return [o for o in orders if o["status"] == "completed"]


@env.task
async def join_region(orders: list[dict], customers: list[dict]) -> list[dict]:
    region_of = {c["customer_id"]: c["region"] for c in customers}
    out = []
    for o in orders:
        reg = region_of.get(o["customer_id"])
        if reg is not None:
            out.append({"region": reg, "amount_cents": o["amount_cents"]})
    return out


@env.task
async def group_by_region(rows: list[dict]) -> list[dict]:
    agg: dict = {}
    for row in rows:
        a = agg.setdefault(row["region"], [0, 0])
        a[0] += 1
        a[1] += row["amount_cents"]
    return [{"region": r, "orders": c, "total_cents": t}
            for r, (c, t) in sorted(agg.items())]


@env.task
async def main(orders: list[dict], customers: list[dict]) -> dict:
    kept = await filter_completed(orders)
    joined = await join_region(kept, customers)
    return {"by_region": await group_by_region(joined)}


if __name__ == "__main__":
    import os
    inp = json.load(open("inputs.json"))
    cfg = os.getenv("FLYTE_AGENT_BENCH_CONFIG")            # set -> run on the cluster
    if cfg:
        flyte.init_from_config(cfg)
        run = flyte.with_runcontext(mode="remote").run(main, **inp)
        run.wait()                                         # remote runs are async
    else:
        flyte.init()                                       # local smoke, no cluster
        run = flyte.run(main, **inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps(run.outputs().o0))
