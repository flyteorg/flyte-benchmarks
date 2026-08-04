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
    inp = json.load(open("inputs.json"))
    r = wf(**inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps({"count": r.count, "mean": r.mean}))
