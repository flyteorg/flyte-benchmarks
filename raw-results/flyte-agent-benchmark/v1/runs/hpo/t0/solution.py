# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["flytekit>=1.13"]
# ///
import functools
import json
import os
import typing

from flytekit import map_task, task, workflow

Output = typing.NamedTuple("Output", best_alpha=float, val_mse=float)


@task
def fit_eval(
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


@task
def pick_best(alphas: list[float], mses: list[float]) -> Output:
    best_idx = min(range(len(mses)), key=lambda i: mses[i])
    return Output(best_alpha=alphas[best_idx], val_mse=round(mses[best_idx], 4))


@workflow
def wf(
    x_train: list[float],
    y_train: list[float],
    x_val: list[float],
    y_val: list[float],
    alphas: list[float],
) -> Output:
    mses = map_task(
        functools.partial(
            fit_eval,
            x_train=x_train,
            y_train=y_train,
            x_val=x_val,
            y_val=y_val,
        )
    )(alpha=alphas)
    return pick_best(alphas=alphas, mses=mses)


def main():
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
            # interactive_mode_enabled: pickle+upload the local code and derive
            # a content-hash version, so the run doesn't depend on the code
            # already being baked into the remote image, and doesn't collide
            # with another trial's same-named "solution.wf".
            interactive_mode_enabled=True,
        )
        ex = remote.execute(wf, inputs=inputs, wait=True)
        best_alpha = ex.outputs["best_alpha"]
        val_mse = ex.outputs["val_mse"]
    else:
        out = wf(**inputs)
        best_alpha = out.best_alpha
        val_mse = out.val_mse

    result = {"best_alpha": float(best_alpha), "val_mse": float(val_mse)}
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))


if __name__ == "__main__":
    main()
