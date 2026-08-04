# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
"""Reference solution (HELD OUT). Spec `batch_inference`, Flyte v2 — batched map."""
import asyncio
import json
import math

import flyte

env = flyte.TaskEnvironment(name="batch_infer")


@env.task
async def infer_batch(batch: list[list[float]], weights: list[float], bias: float) -> list[int]:
    out = []
    for x in batch:
        z = sum(weights[j] * x[j] for j in range(len(x))) + bias
        out.append(1 if 1 / (1 + math.exp(-z)) > 0.5 else 0)
    return out


@env.task
async def main(weights: list[float], bias: float, features: list[list[float]],
               batch_size: int) -> dict:
    batches = [features[i:i + batch_size] for i in range(0, len(features), batch_size)]
    chunks = await asyncio.gather(*[infer_batch(b, weights, bias) for b in batches])
    preds = [p for c in chunks for p in c]        # concat preserves order
    return {"predictions": preds, "positives": sum(preds)}


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))
    flyte.init()
    r = flyte.run(main, **inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps(r.outputs().o0))
