# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["flytekit>=1.13"]
# ///
"""Flyte v1 pipeline: filter completed orders -> join to customer region -> group/aggregate."""
import json
import os

from flytekit import task, workflow


@task
def filter_completed(orders: list[dict]) -> list[dict]:
    return [o for o in orders if o["status"] == "completed"]


@task
def join_region(orders: list[dict], customers: list[dict]) -> list[dict]:
    region_by_customer = {c["customer_id"]: c["region"] for c in customers}
    joined = []
    for o in orders:
        region = region_by_customer.get(o["customer_id"])
        if region is not None:
            joined.append({"region": region, "amount_cents": o["amount_cents"]})
    return joined


@task
def group_by_region(rows: list[dict]) -> list[dict]:
    agg: dict = {}
    for row in rows:
        entry = agg.setdefault(row["region"], {"orders": 0, "total_cents": 0})
        entry["orders"] += 1
        entry["total_cents"] += row["amount_cents"]
    return [
        {"region": region, "orders": v["orders"], "total_cents": v["total_cents"]}
        for region, v in sorted(agg.items())
    ]


@workflow
def wf(orders: list[dict], customers: list[dict]) -> list[dict]:
    completed = filter_completed(orders=orders)
    joined = join_region(orders=completed, customers=customers)
    return group_by_region(rows=joined)


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))
    cfg = os.getenv("FLYTE_AGENT_BENCH_CONFIG")
    if cfg:
        import hashlib

        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote

        remote = FlyteRemote(
            Config.auto(config_file=cfg),
            default_project=os.getenv("FLYTE_BENCH_PROJECT", "flytesnacks"),
            default_domain=os.getenv("FLYTE_BENCH_DOMAIN", "development"),
            interactive_mode_enabled=True,
        )
        # Pin a content-derived version so this script's "solution.wf" entity
        # doesn't collide with a different task's stale "solution.wf" of the
        # same default name already registered under this project/domain.
        version = hashlib.sha1(open(__file__, "rb").read()).hexdigest()[:20]
        ex = remote.execute(wf, inputs=inp, version=version, wait=True)
        result = {"by_region": ex.outputs["o0"]}
    else:
        result = {"by_region": wf(**inp)}

    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))
