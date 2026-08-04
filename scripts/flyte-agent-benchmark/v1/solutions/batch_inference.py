# /// script
# requires-python = ">=3.12"
# dependencies = ["flytekit>=1.13"]
# ///
"""Reference solution (HELD OUT). Spec `batch_inference`, Flyte v1 — batched map.

Chunk -> @dynamic fan-out over batches -> flatten in order -> count.
"""
import json
import math
from typing import NamedTuple

from flytekit import dynamic, task, workflow

Out = NamedTuple("Out", [("predictions", list[int]), ("positives", int)])


@task
def make_batches(features: list[list[float]], batch_size: int) -> list[list[list[float]]]:
    return [features[i:i + batch_size] for i in range(0, len(features), batch_size)]


@task
def infer_batch(batch: list[list[float]], weights: list[float], bias: float) -> list[int]:
    out = []
    for x in batch:
        z = sum(weights[j] * x[j] for j in range(len(x))) + bias
        out.append(1 if 1 / (1 + math.exp(-z)) > 0.5 else 0)
    return out


@dynamic
def run_batches(batches: list[list[list[float]]], weights: list[float],
                bias: float) -> list[list[int]]:
    return [infer_batch(batch=b, weights=weights, bias=bias) for b in batches]


@task
def finalize(chunks: list[list[int]]) -> Out:
    preds = [p for c in chunks for p in c]        # concat preserves batch order
    return Out(predictions=preds, positives=sum(preds))


@workflow
def wf(weights: list[float], bias: float, features: list[list[float]],
       batch_size: int) -> Out:
    batches = make_batches(features=features, batch_size=batch_size)
    chunks = run_batches(batches=batches, weights=weights, bias=bias)
    return finalize(chunks=chunks)


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
        result = {"predictions": list(out["predictions"]), "positives": out["positives"]}
    else:                                                 # local smoke, no cluster
        r = wf(**inp)
        result = {"predictions": list(r.predictions), "positives": r.positives}
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))
