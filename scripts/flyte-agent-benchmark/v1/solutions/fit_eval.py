# /// script
# requires-python = ">=3.12"
# dependencies = ["flytekit>=1.13"]
# ///
"""Reference solution (HELD OUT). Spec `fit_eval`, Flyte v1 — multi-stage.

fit -> evaluate, passing slope/intercept between tasks. Full precision flows
between tasks; rounding happens only at the output boundary so the MSE matches
the oracle's unrounded reference.
"""
import json
from typing import NamedTuple

from flytekit import task, workflow

Fit = NamedTuple("Fit", [("slope", float), ("intercept", float)])
Out = NamedTuple("Out", [("slope", float), ("intercept", float), ("mse", float)])


@task
def fit(x: list[int], y: list[int]) -> Fit:
    n = len(x)
    sx, sy = sum(x), sum(y)
    sxx = sum(v * v for v in x)
    sxy = sum(x[i] * y[i] for i in range(n))
    m = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    b = (sy - m * sx) / n
    return Fit(slope=m, intercept=b)


@task
def evaluate(x: list[int], y: list[int], slope: float, intercept: float) -> float:
    n = len(x)
    return sum((y[i] - (slope * x[i] + intercept)) ** 2 for i in range(n)) / n


@workflow
def wf(x: list[int], y: list[int]) -> Out:
    f = fit(x=x, y=y)
    mse = evaluate(x=x, y=y, slope=f.slope, intercept=f.intercept)
    return Out(slope=f.slope, intercept=f.intercept, mse=mse)


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))
    r = wf(**inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps({
        "slope": round(r.slope, 4),
        "intercept": round(r.intercept, 4),
        "mse": round(r.mse, 4),
    }))
