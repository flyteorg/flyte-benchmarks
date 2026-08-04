# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["flytekit>=1.13"]
# ///
import functools
import json
import math
import os
from typing import NamedTuple

from flytekit import map_task, task, workflow


@task
def split_batches(
    features: list[list[float]], batch_size: int
) -> list[list[list[float]]]:
    return [
        features[i : i + batch_size] for i in range(0, len(features), batch_size)
    ]


@task
def infer_batch(
    batch: list[list[float]], weights: list[float], bias: float
) -> list[int]:
    preds = []
    for row in batch:
        z = sum(w * x for w, x in zip(weights, row)) + bias
        sig = 1.0 / (1.0 + math.exp(-z))
        preds.append(1 if sig > 0.5 else 0)
    return preds


class Out(NamedTuple):
    predictions: list[int]
    positives: int


@task
def combine(batch_predictions: list[list[int]]) -> Out:
    predictions = [p for batch in batch_predictions for p in batch]
    positives = sum(predictions)
    return Out(predictions=predictions, positives=positives)


@workflow
def wf(
    weights: list[float],
    bias: float,
    features: list[list[float]],
    batch_size: int,
) -> Out:
    batches = split_batches(features=features, batch_size=batch_size)
    bound_infer = functools.partial(infer_batch, weights=weights, bias=bias)
    batch_predictions = map_task(bound_infer)(batch=batches)
    return combine(batch_predictions=batch_predictions)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    config_file = os.environ.get("FLYTE_AGENT_BENCH_CONFIG") or os.environ.get(
        "FLYTECTL_CONFIG"
    )

    if config_file:
        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote

        remote = FlyteRemote(
            Config.auto(config_file=config_file),
            default_project="flytesnacks",
            default_domain="development",
            interactive_mode_enabled=True,  # pickle-based fast register; avoids
            # relying on the script being import-able by filename inside the pod
        )
        ex = remote.execute(wf, inputs=inputs, wait=True)
        predictions = ex.outputs["predictions"]
        positives = ex.outputs["positives"]
    else:
        out = wf(**inputs)
        predictions = out.predictions
        positives = out.positives

    print(
        "TRIAL_OUTPUT_JSON:"
        + json.dumps({"predictions": predictions, "positives": positives})
    )
