# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["flytekit>=1.13"]
# ///
"""Flyte v1 (flytekit) solution for the batch_inference spec.

Splits `features` into consecutive batches of `batch_size` rows (last batch
may be smaller). Since the number/size of batches depends on the runtime
length of `features`, the split has to happen inside a `@dynamic` workflow
(its body runs at execution time with real Python values). Each batch is
scored by its own `score_batch` task call -- the calls are independent of
one another so Flyte schedules them in parallel, giving "one inference task
per batch, in parallel". A `flatten` task concatenates the per-batch Promise
lists (in original batch order, so overall row order is preserved) into the
final predictions list.

Reads weights/bias/features/batch_size from inputs.json in the cwd, submits
+ waits on the configured Flyte cluster (falls back to a local run if
FLYTE_AGENT_BENCH_CONFIG is not set), and prints one line:
TRIAL_OUTPUT_JSON:{"predictions": [...], "positives": ...}
"""
import json
import math
import os
from pathlib import Path

from flytekit import dynamic, task, workflow


@task
def score_batch(weights: list[float], bias: float, batch: list[list[float]]) -> list[int]:
    preds = []
    for row in batch:
        z = sum(w * x for w, x in zip(weights, row)) + bias
        sig = 1.0 / (1.0 + math.exp(-z))
        preds.append(1 if sig > 0.5 else 0)
    return preds


@task
def flatten(chunks: list[list[int]]) -> list[int]:
    out: list[int] = []
    for c in chunks:
        out.extend(c)
    return out


@dynamic
def run_batches(
    weights: list[float], bias: float, features: list[list[float]], batch_size: int
) -> list[int]:
    batches = [features[i : i + batch_size] for i in range(0, len(features), batch_size)]
    results = [score_batch(weights=weights, bias=bias, batch=b) for b in batches]
    return flatten(chunks=results)


@workflow
def wf(
    weights: list[float], bias: float, features: list[list[float]], batch_size: int
) -> list[int]:
    return run_batches(weights=weights, bias=bias, features=features, batch_size=batch_size)


if __name__ == "__main__":
    here = Path(__file__).parent
    inputs = json.loads((here / "inputs.json").read_text())

    weights = [float(w) for w in inputs["weights"]]
    bias = float(inputs["bias"])
    features = [[float(x) for x in row] for row in inputs["features"]]
    batch_size = int(inputs["batch_size"])

    config_file = os.environ.get("FLYTE_AGENT_BENCH_CONFIG") or os.environ.get("FLYTECTL_CONFIG")

    if config_file:
        import hashlib

        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote

        remote = FlyteRemote(
            Config.auto(config_file=config_file),
            default_project="flytesnacks",
            default_domain="development",
        )

        # Content-unique version so registration can't collide with a
        # same-named `wf` from a different trial/spec on the shared
        # project/domain.
        version = "batchinf-" + hashlib.sha1(
            Path(__file__).read_bytes()
        ).hexdigest()[:16]

        # register_script fast-packages this local file so the remote pod can
        # actually import it (a bare remote.execute() assumes the task code
        # is already baked into the image, which it isn't here).
        flyte_wf = remote.register_script(
            wf,
            version=version,
            source_path=str(here),
            module_name="solution",
        )

        ex = remote.execute(
            flyte_wf,
            inputs={
                "weights": weights,
                "bias": bias,
                "features": features,
                "batch_size": batch_size,
            },
            wait=True,
        )
        predictions = list(ex.outputs["o0"])
    else:
        predictions = list(
            wf(weights=weights, bias=bias, features=features, batch_size=batch_size)
        )

    result = {
        "predictions": [int(p) for p in predictions],
        "positives": int(sum(predictions)),
    }
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))
