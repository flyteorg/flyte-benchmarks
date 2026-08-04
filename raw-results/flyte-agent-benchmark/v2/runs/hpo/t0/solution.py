# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
import asyncio
import json
import os

import flyte

env = flyte.TaskEnvironment(name="hpo")


@env.task
async def fit_and_eval(
    x_train: list[float],
    y_train: list[float],
    x_val: list[float],
    y_val: list[float],
    alpha: float,
) -> tuple[float, float]:
    sxy = sum(x * y for x, y in zip(x_train, y_train))
    sxx = sum(x * x for x in x_train)
    w = sxy / (sxx + alpha)
    mse = sum((w * x - y) ** 2 for x, y in zip(x_val, y_val)) / len(y_val)
    return alpha, mse


@env.task
async def main(
    x_train: list[float],
    y_train: list[float],
    x_val: list[float],
    y_val: list[float],
    alphas: list[float],
) -> dict[str, float]:
    results = await asyncio.gather(
        *[fit_and_eval(x_train, y_train, x_val, y_val, a) for a in alphas]
    )
    best_alpha, best_mse = min(results, key=lambda r: r[1])
    return {"best_alpha": best_alpha, "val_mse": round(best_mse, 4)}


if __name__ == "__main__":
    with open("inputs.json") as f:
        inputs = json.load(f)

    cfg = os.getenv("FLYTE_AGENT_BENCH_CONFIG")  # set -> run on the cluster

    if cfg:
        flyte.init_from_config(cfg)
        run = flyte.with_runcontext(mode="remote").run(
            main,
            x_train=inputs["x_train"],
            y_train=inputs["y_train"],
            x_val=inputs["x_val"],
            y_val=inputs["y_val"],
            alphas=inputs["alphas"],
        )
        print(run.name, run.url)
        run.wait()
        out = run.outputs().o0
    else:
        flyte.init()
        out = flyte.run(
            main,
            x_train=inputs["x_train"],
            y_train=inputs["y_train"],
            x_val=inputs["x_val"],
            y_val=inputs["y_val"],
            alphas=inputs["alphas"],
        )

    print("TRIAL_OUTPUT_JSON:" + json.dumps(out))
