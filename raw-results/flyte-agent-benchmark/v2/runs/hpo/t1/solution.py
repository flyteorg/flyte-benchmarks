import asyncio
import json
import os

import flyte

env = flyte.TaskEnvironment(name="hpo_ridge")


@env.task
async def fit_and_eval(alpha: float, x_train: list[float], y_train: list[float],
                        x_val: list[float], y_val: list[float]) -> float:
    sxx = sum(x * x for x in x_train)
    sxy = sum(x_train[i] * y_train[i] for i in range(len(x_train)))
    w = sxy / (sxx + alpha)
    mse = sum((y_val[i] - w * x_val[i]) ** 2 for i in range(len(x_val))) / len(x_val)
    return mse


@env.task
async def main(x_train: list[float], y_train: list[float], x_val: list[float],
                y_val: list[float], alphas: list[float]) -> dict:
    mses = await asyncio.gather(
        *[fit_and_eval(a, x_train, y_train, x_val, y_val) for a in alphas]
    )
    best_i = min(range(len(alphas)), key=lambda i: mses[i])
    return {"best_alpha": alphas[best_i], "val_mse": round(mses[best_i], 4)}


if __name__ == "__main__":
    inputs = json.load(open("inputs.json"))
    cfg = os.getenv("FLYTE_AGENT_BENCH_CONFIG")
    if cfg:
        flyte.init_from_config(cfg)
        run = flyte.with_runcontext(mode="remote").run(main, **inputs)
        print(run.name, run.url)
        run.wait()
        outputs = run.outputs().o0
    else:
        flyte.init()
        run = flyte.run(main, **inputs)
        outputs = run.outputs().o0 if hasattr(run, "outputs") else run

    print("TRIAL_OUTPUT_JSON:" + json.dumps(outputs))
