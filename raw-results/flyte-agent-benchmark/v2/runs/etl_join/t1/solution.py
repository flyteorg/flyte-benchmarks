# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
import json
import os
from pathlib import Path

import flyte

env = flyte.TaskEnvironment(name="etl_join")


@env.task
async def filter_completed(orders: list[dict]) -> list[dict]:
    return [o for o in orders if o["status"] == "completed"]


@env.task
async def join_region(orders: list[dict], customers: list[dict]) -> list[dict]:
    cust_region = {c["customer_id"]: c["region"] for c in customers}
    joined = []
    for o in orders:
        region = cust_region.get(o["customer_id"])
        if region is not None:
            joined.append({"region": region, "amount_cents": o["amount_cents"]})
    return joined


@env.task
async def group_by_region(joined: list[dict]) -> list[dict]:
    agg: dict[str, dict] = {}
    for j in joined:
        r = j["region"]
        if r not in agg:
            agg[r] = {"region": r, "orders": 0, "total_cents": 0}
        agg[r]["orders"] += 1
        agg[r]["total_cents"] += j["amount_cents"]
    return sorted(agg.values(), key=lambda x: x["region"])


@env.task
async def main(orders: list[dict], customers: list[dict]) -> list[dict]:
    completed = await filter_completed(orders)
    joined = await join_region(completed, customers)
    return await group_by_region(joined)


if __name__ == "__main__":
    inputs = json.loads(
        Path(__file__).parent.joinpath("inputs.json").read_text()
    )

    config_path = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")
    if config_path:
        flyte.init_from_config(config_path)
        run = flyte.with_runcontext(mode="remote").run(
            main, orders=inputs["orders"], customers=inputs["customers"]
        )
        print(run.name, run.url)
        run.wait()
        by_region = run.outputs().o0
    else:
        flyte.init()
        by_region = flyte.run(
            main, orders=inputs["orders"], customers=inputs["customers"]
        )

    print("TRIAL_OUTPUT_JSON:" + json.dumps({"by_region": by_region}))
