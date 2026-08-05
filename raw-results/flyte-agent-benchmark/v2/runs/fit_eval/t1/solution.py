# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
import json
import os

import flyte

env = flyte.TaskEnvironment(name="fit_eval")


@env.task
async def fit(x: list[float], y: list[float]) -> list[float]:
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den = sum((xi - mean_x) ** 2 for xi in x)
    m = num / den
    b = mean_y - m * mean_x
    return [m, b]


@env.task
async def evaluate(x: list[float], y: list[float], m: float, b: float) -> float:
    n = len(x)
    sq_errors = [(yi - (m * xi + b)) ** 2 for xi, yi in zip(x, y)]
    return sum(sq_errors) / n


@env.task
async def main(x: list[float], y: list[float]) -> list[float]:
    m, b = await fit(x, y)
    mse = await evaluate(x, y, m, b)
    return [m, b, mse]


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)
    x = [float(v) for v in inputs["x"]]
    y = [float(v) for v in inputs["y"]]

    config_path = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")
    if config_path:
        flyte.init_from_config(config_path)
        run = flyte.with_runcontext(mode="remote").run(main, x=x, y=y)
        print(run.name, run.url)
        run.wait()
        result = run.outputs().o0
    else:
        flyte.init()
        result = flyte.run(main, x=x, y=y)

    slope, intercept, mse = result
    output = {
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "mse": round(mse, 4),
    }
    print(f"TRIAL_OUTPUT_JSON:{json.dumps(output)}")
