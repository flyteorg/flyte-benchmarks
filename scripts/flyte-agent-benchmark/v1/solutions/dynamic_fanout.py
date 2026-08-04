# /// script
# requires-python = ">=3.12"
# dependencies = ["flytekit>=1.13"]
# ///
"""Reference solution (HELD OUT). Spec `dynamic_fanout`, Flyte v1 — @dynamic.

N is decided at runtime by `count`, so the fan-out lives in a @dynamic whose
body runs at execution time (real int `n`). The per-leaf results are Promises
inside the dynamic, so they are summed by a downstream task, not with `sum()`.
"""
import json
from typing import NamedTuple

from flytekit import dynamic, task, workflow

Out = NamedTuple("Out", [("n", int), ("total", int)])


@task
def count(seed: int) -> int:
    return (seed % 5) + 3


@task
def work(i: int) -> int:
    return i * i


@task
def total_of(vals: list[int]) -> int:
    return sum(vals)


@dynamic
def fan(n: int) -> int:
    return total_of(vals=[work(i=i) for i in range(n)])


@workflow
def wf(seed: int) -> Out:
    n = count(seed=seed)
    return Out(n=n, total=fan(n=n))


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
        result = {"n": out["n"], "total": out["total"]}
    else:                                                 # local smoke, no cluster
        r = wf(**inp)
        result = {"n": r.n, "total": r.total}
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))
