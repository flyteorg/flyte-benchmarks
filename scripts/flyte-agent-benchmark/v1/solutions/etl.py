# /// script
# requires-python = ">=3.12"
# dependencies = ["flytekit>=1.13"]
# ///
"""Reference solution (HELD OUT — never show to the agent under test).

Spec `etl`, Flyte v1. Local execution: a @workflow called at top level runs
in-process and returns real values. Prints TRIAL_OUTPUT_JSON for oracle.py.
"""
import json
from typing import NamedTuple

from flytekit import task, workflow

Out = NamedTuple("Out", [("count", int), ("mean", float)])


@task
def clean(readings: list[int]) -> list[int]:
    return [r for r in readings if r >= 0]


@task
def aggregate(xs: list[int]) -> Out:
    c = len(xs)
    return Out(count=c, mean=round(sum(xs) / c, 3) if c else 0.0)


@workflow
def wf(readings: list[int]) -> Out:
    return aggregate(xs=clean(readings=readings))


if __name__ == "__main__":
    import os
    inp = json.load(open("inputs.json"))
    cfg = os.getenv("FLYTE_AGENT_BENCH_CONFIG")            # set -> run on the cluster
    if cfg:                                                # remote: submit + fetch outputs
        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote
        remote = FlyteRemote(Config.auto(config_file=cfg),
                             default_project=os.getenv("FLYTE_BENCH_PROJECT", "flytesnacks"),
                             default_domain=os.getenv("FLYTE_BENCH_DOMAIN", "development"))
        out = remote.execute(wf, inputs=inp, wait=True).outputs   # auto-registers + runs + waits
        result = {"count": out["count"], "mean": out["mean"]}
    else:                                                 # local smoke, no cluster
        r = wf(**inp)
        result = {"count": r.count, "mean": r.mean}
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))
