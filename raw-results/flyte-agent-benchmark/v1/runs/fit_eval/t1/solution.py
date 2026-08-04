# /// script
# requires-python = "==3.12.*"
# dependencies = ["flytekit>=1.13"]
# ///
import json
import os
from typing import NamedTuple

from flytekit import task, workflow


class FitOutput(NamedTuple):
    m: float
    b: float


@task
def fit(x: list[float], y: list[float]) -> FitOutput:
    n = len(x)
    sx = sum(x)
    sy = sum(y)
    sxx = sum(v * v for v in x)
    sxy = sum(x[i] * y[i] for i in range(n))
    denom = n * sxx - sx * sx
    m = (n * sxy - sx * sy) / denom
    b = (sy - m * sx) / n
    return FitOutput(m=m, b=b)


@task
def evaluate(x: list[float], y: list[float], m: float, b: float) -> float:
    n = len(x)
    return sum((y[i] - (m * x[i] + b)) ** 2 for i in range(n)) / n


class WfOutput(NamedTuple):
    slope: float
    intercept: float
    mse: float


@workflow
def wf(x: list[float], y: list[float]) -> WfOutput:
    fit_out = fit(x=x, y=y)
    mse = evaluate(x=x, y=y, m=fit_out.m, b=fit_out.b)
    return WfOutput(slope=fit_out.m, intercept=fit_out.b, mse=mse)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    x = [float(v) for v in inputs["x"]]
    y = [float(v) for v in inputs["y"]]

    config_file = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")

    if config_file:
        import uuid

        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote

        remote = FlyteRemote(
            Config.auto(config_file=config_file),
            default_project="flytesnacks",
            default_domain="development",
            # Non-interactive script execution: without this, FlyteRemote never
            # pickles+uploads the local module, so the remote pod tries to
            # `import solution` and fails with ModuleNotFoundError.
            interactive_mode_enabled=True,
        )
        # Use a unique version so this registration never collides with (or
        # accidentally fetches) an unrelated, differently-shaped "solution.wf"
        # entity already registered under this project/domain by another
        # trial's script of the same module/function name.
        ex = remote.execute(
            wf,
            inputs={"x": x, "y": y},
            version=f"fiteval{uuid.uuid4().hex[:12]}",
            wait=True,
        )
        slope = ex.outputs["slope"]
        intercept = ex.outputs["intercept"]
        mse = ex.outputs["mse"]
    else:
        out = wf(x=x, y=y)
        slope, intercept, mse = out.slope, out.intercept, out.mse

    result = {
        "slope": round(float(slope), 4),
        "intercept": round(float(intercept), 4),
        "mse": round(float(mse), 4),
    }
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))


if __name__ == "__main__":
    main()
