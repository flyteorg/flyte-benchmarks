# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
import asyncio
import json
import math
import os

import flyte

env = flyte.TaskEnvironment(name="batch_inference")


@env.task
async def infer_batch(
    rows: list[list[float]], weights: list[float], bias: float
) -> list[int]:
    preds: list[int] = []
    for row in rows:
        z = bias + sum(w * f for w, f in zip(weights, row))
        sig = 1.0 / (1.0 + math.exp(-z))
        preds.append(1 if sig > 0.5 else 0)
    return preds


@env.task
async def main(
    weights: list[float],
    bias: float,
    features: list[list[float]],
    batch_size: int,
) -> tuple[list[int], int]:
    batches = [
        features[i : i + batch_size] for i in range(0, len(features), batch_size)
    ]
    batch_results = await asyncio.gather(
        *[infer_batch(b, weights, bias) for b in batches]
    )
    predictions: list[int] = []
    for br in batch_results:
        predictions.extend(br)
    positives = sum(predictions)
    return predictions, positives


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    config_path = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")
    if config_path:
        flyte.init_from_config(config_path)
        run = flyte.with_runcontext(mode="remote").run(
            main,
            weights=inputs["weights"],
            bias=inputs["bias"],
            features=inputs["features"],
            batch_size=inputs["batch_size"],
        )
        print(run.name, run.url)
        run.wait()
        outputs = run.outputs()
        predictions = outputs.o0
        positives = outputs.o1
    else:
        flyte.init()
        predictions, positives = flyte.run(
            main,
            weights=inputs["weights"],
            bias=inputs["bias"],
            features=inputs["features"],
            batch_size=inputs["batch_size"],
        )

    result = {"predictions": list(predictions), "positives": int(positives)}
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))
