# /// script
# requires-python = "==3.12.*"
# dependencies = ["flytekit>=1.13"]
# ///
import json
import os
from pathlib import Path

from flytekit import task, workflow


@task
def filter_completed(orders: list[dict]) -> list[dict]:
    return [o for o in orders if o["status"] == "completed"]


@task
def join_customers(orders: list[dict], customers: list[dict]) -> list[dict]:
    region_by_customer = {c["customer_id"]: c["region"] for c in customers}
    joined = []
    for o in orders:
        region = region_by_customer.get(o["customer_id"])
        if region is not None:
            joined.append({"region": region, "amount_cents": o["amount_cents"]})
    return joined


@task
def group_by_region(joined: list[dict]) -> list[dict]:
    agg: dict[str, dict] = {}
    for row in joined:
        region = row["region"]
        bucket = agg.setdefault(region, {"region": region, "orders": 0, "total_cents": 0})
        bucket["orders"] += 1
        bucket["total_cents"] += row["amount_cents"]
    return sorted(agg.values(), key=lambda r: r["region"])


@workflow
def wf(orders: list[dict], customers: list[dict]) -> list[dict]:
    completed = filter_completed(orders=orders)
    joined = join_customers(orders=completed, customers=customers)
    return group_by_region(joined=joined)


if __name__ == "__main__":
    here = Path(__file__).parent
    inputs = json.loads((here / "inputs.json").read_text())

    config_file = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")

    if config_file:
        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote

        remote = FlyteRemote(
            Config.auto(config_file=config_file),
            default_project="flytesnacks",
            default_domain="development",
            interactive_mode_enabled=True,  # pickle+upload code so the pod doesn't need to import this script as a module
        )
        import time

        version = f"etljoin{int(time.time())}"
        ex = remote.execute(
            wf,
            inputs={"orders": inputs["orders"], "customers": inputs["customers"]},
            version=version,
            wait=True,
        )
        by_region = ex.outputs["o0"]
    else:
        by_region = wf(orders=inputs["orders"], customers=inputs["customers"])

    result = {"by_region": by_region}
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))
