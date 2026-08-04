# /// script
# requires-python = "==3.12.*"
# dependencies = ["flytekit>=1.13"]
# ///
import json
import os
from typing import NamedTuple

from flytekit import task, workflow

FitOutput = NamedTuple("FitOutput", slope=float, intercept=float)


@task
def fit(x: list[float], y: list[float]) -> FitOutput:
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den = sum((xi - mean_x) ** 2 for xi in x)
    m = num / den
    b = mean_y - m * mean_x
    return FitOutput(slope=m, intercept=b)


@task
def evaluate(x: list[float], y: list[float], slope: float, intercept: float) -> float:
    n = len(x)
    mse = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y)) / n
    return mse


@workflow
def wf(x: list[float], y: list[float]) -> tuple[float, float, float]:
    fit_out = fit(x=x, y=y)
    mse = evaluate(x=x, y=y, slope=fit_out.slope, intercept=fit_out.intercept)
    return fit_out.slope, fit_out.intercept, mse


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    x = [float(v) for v in inputs["x"]]
    y = [float(v) for v in inputs["y"]]

    config_file = os.environ.get("FLYTE_AGENT_BENCH_CONFIG") or os.environ.get("FLYTECTL_CONFIG")

    if config_file:
        import uuid

        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote

        remote = FlyteRemote(
            Config.auto(config_file=config_file),
            default_project="flytesnacks",
            default_domain="development",
        )

        version = uuid.uuid4().hex
        # Fast-register: package + upload this script's source so the remote
        # pod can import it (a bare remote.execute(wf, ...) leaves the task
        # code unavailable in the default image).
        remote.register_script(
            wf,
            version=version,
            project="flytesnacks",
            domain="development",
            source_path=here,
            module_name="solution",
        )
        ex = remote.execute(wf, inputs={"x": x, "y": y}, wait=True, version=version)
        slope = ex.outputs["o0"]
        intercept = ex.outputs["o1"]
        mse = ex.outputs["o2"]
    else:
        slope, intercept, mse = wf(x=x, y=y)

    result = {
        "slope": round(float(slope), 4),
        "intercept": round(float(intercept), 4),
        "mse": round(float(mse), 4),
    }
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))


if __name__ == "__main__":
    main()
