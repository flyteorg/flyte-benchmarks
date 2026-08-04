# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
"""Reference solution (HELD OUT). Spec `hpo`, Flyte v2 — gather sweep + argmin.

Closed-form ridge (equivalent to sklearn Ridge(fit_intercept=False)) keeps the
grade deterministic; the sweep is a native gather over the candidate alphas.
"""
import asyncio
import json

import flyte

env = flyte.TaskEnvironment(name="hpo")


@env.task
async def val_mse(alpha: float, x_train: list[float], y_train: list[float],
                  x_val: list[float], y_val: list[float]) -> float:
    sxx = sum(v * v for v in x_train)
    sxy = sum(x_train[i] * y_train[i] for i in range(len(x_train)))
    w = sxy / (sxx + alpha)
    return sum((y_val[i] - w * x_val[i]) ** 2 for i in range(len(x_val))) / len(x_val)


@env.task
async def main(x_train: list[float], y_train: list[float], x_val: list[float],
               y_val: list[float], alphas: list[float]) -> dict:
    mses = await asyncio.gather(
        *[val_mse(a, x_train, y_train, x_val, y_val) for a in alphas])
    i = min(range(len(mses)), key=lambda i: mses[i])
    return {"best_alpha": alphas[i], "val_mse": round(mses[i], 4)}


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))
    flyte.init()
    r = flyte.run(main, **inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps(r.outputs().o0))
