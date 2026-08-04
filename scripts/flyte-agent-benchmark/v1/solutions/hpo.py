# /// script
# requires-python = ">=3.12"
# dependencies = ["flytekit>=1.13"]
# ///
"""Reference solution (HELD OUT). Spec `hpo`, Flyte v1 — @dynamic sweep + reduce.

The alpha sweep is a runtime fan-out, so it lives in a @dynamic; a downstream
task reduces the per-alpha MSEs to the best. Closed-form ridge keeps grading
deterministic (equivalent to sklearn Ridge(fit_intercept=False)).
"""
import json
from typing import NamedTuple

from flytekit import dynamic, task, workflow

Best = NamedTuple("Best", [("best_alpha", float), ("val_mse", float)])


@task
def val_mse(alpha: float, x_train: list[float], y_train: list[float],
            x_val: list[float], y_val: list[float]) -> float:
    sxx = sum(v * v for v in x_train)
    sxy = sum(x_train[i] * y_train[i] for i in range(len(x_train)))
    w = sxy / (sxx + alpha)
    return sum((y_val[i] - w * x_val[i]) ** 2 for i in range(len(x_val))) / len(x_val)


@task
def pick_best(alphas: list[float], mses: list[float]) -> Best:
    i = min(range(len(mses)), key=lambda i: mses[i])
    return Best(best_alpha=alphas[i], val_mse=round(mses[i], 4))


@dynamic
def sweep(x_train: list[float], y_train: list[float], x_val: list[float],
          y_val: list[float], alphas: list[float]) -> Best:
    mses = [val_mse(alpha=a, x_train=x_train, y_train=y_train,
                    x_val=x_val, y_val=y_val) for a in alphas]
    return pick_best(alphas=alphas, mses=mses)


@workflow
def wf(x_train: list[float], y_train: list[float], x_val: list[float],
       y_val: list[float], alphas: list[float]) -> Best:
    return sweep(x_train=x_train, y_train=y_train, x_val=x_val,
                 y_val=y_val, alphas=alphas)


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))
    r = wf(**inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps(
        {"best_alpha": r.best_alpha, "val_mse": r.val_mse}))
