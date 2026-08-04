# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
"""Reference solution (HELD OUT). Spec `fit_eval`, Flyte v2 — multi-stage."""
import json

import flyte

env = flyte.TaskEnvironment(name="fit")


@env.task
async def fit(x: list[int], y: list[int]) -> dict:
    n = len(x)
    sx, sy = sum(x), sum(y)
    sxx = sum(v * v for v in x)
    sxy = sum(x[i] * y[i] for i in range(n))
    m = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    b = (sy - m * sx) / n
    return {"slope": m, "intercept": b}       # full precision between tasks


@env.task
async def evaluate(x: list[int], y: list[int], slope: float, intercept: float) -> float:
    n = len(x)
    return sum((y[i] - (slope * x[i] + intercept)) ** 2 for i in range(n)) / n


@env.task
async def main(x: list[int], y: list[int]) -> dict:
    f = await fit(x, y)
    mse = await evaluate(x, y, f["slope"], f["intercept"])
    return {"slope": round(f["slope"], 4),
            "intercept": round(f["intercept"], 4),
            "mse": round(mse, 4)}


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))
    flyte.init()
    r = flyte.run(main, **inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps(r.outputs().o0))
