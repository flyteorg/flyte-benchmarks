import asyncio
import json
import math
import os

import flyte

env = flyte.TaskEnvironment(name="batch_inference")


@env.task
async def infer_batch(
    weights: list[float], bias: float, batch: list[list[float]]
) -> list[int]:
    preds = []
    for row in batch:
        z = bias + sum(w * x for w, x in zip(weights, row))
        prob = 1.0 / (1.0 + math.exp(-z))
        preds.append(1 if prob > 0.5 else 0)
    return preds


@env.task
async def main(
    weights: list[float],
    bias: float,
    features: list[list[float]],
    batch_size: int,
) -> list[int]:
    batches = [
        features[i : i + batch_size] for i in range(0, len(features), batch_size)
    ]
    results = await asyncio.gather(
        *[infer_batch(weights, bias, batch) for batch in batches]
    )
    predictions: list[int] = []
    for batch_result in results:
        predictions.extend(batch_result)
    return predictions


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
        predictions = run.outputs().o0
    else:
        flyte.init()
        predictions = flyte.run(
            main,
            weights=inputs["weights"],
            bias=inputs["bias"],
            features=inputs["features"],
            batch_size=inputs["batch_size"],
        )

    predictions = list(predictions)
    positives = sum(predictions)
    print(
        "TRIAL_OUTPUT_JSON:"
        + json.dumps({"predictions": predictions, "positives": positives})
    )
