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
    inp = json.load(open("inputs.json"))
    r = wf(**inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps({"n": r.n, "total": r.total}))
