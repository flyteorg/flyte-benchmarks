# /// script
# requires-python = "==3.12.*"
# dependencies = ["flytekit>=1.13"]
# ///
import functools
import hashlib
import json
import os
from typing import NamedTuple

from flytekit import map_task, task, workflow


@task
def fit_and_eval(
    alpha: float,
    x_train: list[float],
    y_train: list[float],
    x_val: list[float],
    y_val: list[float],
) -> float:
    sxy = sum(x * y for x, y in zip(x_train, y_train))
    sxx = sum(x * x for x in x_train)
    w = sxy / (sxx + alpha)
    mse = sum((y - w * x) ** 2 for x, y in zip(x_val, y_val)) / len(x_val)
    return mse


class HPOResult(NamedTuple):
    best_alpha: float
    val_mse: float


@task
def pick_best(alphas: list[float], mses: list[float]) -> HPOResult:
    best_idx = min(range(len(mses)), key=lambda i: mses[i])
    return HPOResult(best_alpha=alphas[best_idx], val_mse=round(mses[best_idx], 4))


@workflow
def wf(
    x_train: list[float],
    y_train: list[float],
    x_val: list[float],
    y_val: list[float],
    alphas: list[float],
) -> HPOResult:
    mapped = functools.partial(
        fit_and_eval,
        x_train=x_train,
        y_train=y_train,
        x_val=x_val,
        y_val=y_val,
    )
    mses = map_task(mapped)(alpha=alphas)
    return pick_best(alphas=alphas, mses=mses)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    config_file = os.environ.get("FLYTE_AGENT_BENCH_CONFIG") or os.environ.get("FLYTECTL_CONFIG")

    if config_file:
        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote

        remote = FlyteRemote(
            Config.auto(config_file=config_file),
            default_project="flytesnacks",
            default_domain="development",
            interactive_mode_enabled=True,
        )
        # Force a fresh, content-addressed version so this workflow never
        # collides with a stale "wf"-named registration from another trial.
        version = "hpo-t1-" + hashlib.sha1(open(__file__, "rb").read()).hexdigest()[:16]
        ex = remote.execute(wf, inputs=inputs, wait=True, version=version)
        out = {
            "best_alpha": ex.outputs["best_alpha"],
            "val_mse": ex.outputs["val_mse"],
        }
    else:
        result = wf(**inputs)
        out = {"best_alpha": result.best_alpha, "val_mse": result.val_mse}

    print("TRIAL_OUTPUT_JSON:" + json.dumps(out))
