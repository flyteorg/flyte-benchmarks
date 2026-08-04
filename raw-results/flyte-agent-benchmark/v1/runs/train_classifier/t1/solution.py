# /// script
# requires-python = "==3.12.*"
# dependencies = ["flytekit>=1.13"]
# ///
import json
import os
import uuid
from typing import NamedTuple

from flytekit import task, workflow

TrainOutput = NamedTuple("TrainOutput", c0=list[float], c1=list[float])


@task
def train(X_train: list[list[float]], y_train: list[int]) -> TrainOutput:
    """Fit a nearest-centroid binary classifier: compute the mean feature
    vector (centroid) of each class."""
    sum0 = [0.0, 0.0]
    sum1 = [0.0, 0.0]
    n0 = 0
    n1 = 0
    for x, y in zip(X_train, y_train):
        if int(y) == 0:
            sum0[0] += x[0]
            sum0[1] += x[1]
            n0 += 1
        else:
            sum1[0] += x[0]
            sum1[1] += x[1]
            n1 += 1
    c0 = [sum0[0] / n0, sum0[1] / n0]
    c1 = [sum1[0] / n1, sum1[1] / n1]
    return TrainOutput(c0=c0, c1=c1)


@task
def predict(X_test: list[list[float]], c0: list[float], c1: list[float]) -> list[int]:
    """Assign each test row to the class whose centroid is nearest
    (Euclidean distance)."""
    preds = []
    for x in X_test:
        d0 = (x[0] - c0[0]) ** 2 + (x[1] - c0[1]) ** 2
        d1 = (x[0] - c1[0]) ** 2 + (x[1] - c1[1]) ** 2
        preds.append(0 if d0 <= d1 else 1)
    return preds


@workflow
def wf(X_train: list[list[float]], y_train: list[int], X_test: list[list[float]]) -> list[int]:
    trained = train(X_train=X_train, y_train=y_train)
    return predict(X_test=X_test, c0=trained.c0, c1=trained.c1)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    X_train = [[float(v) for v in row] for row in inputs["X_train"]]
    y_train = [int(v) for v in inputs["y_train"]]
    X_test = [[float(v) for v in row] for row in inputs["X_test"]]

    config_file = os.environ.get("FLYTE_AGENT_BENCH_CONFIG") or os.environ.get("FLYTECTL_CONFIG")

    if config_file:
        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote

        remote = FlyteRemote(
            Config.auto(config_file=config_file),
            default_project="flytesnacks",
            default_domain="development",
        )

        # `remote.execute(wf, ...)` registers via FlyteRemote.register_workflow,
        # which (when not in interactive/pickling mode) assumes the task code
        # is already baked into the container image -- it never uploads this
        # script. On a generic default image that means the pod can never
        # import this module. Explicitly fast-register via `register_script`
        # so the source is packaged and shipped to the executing pod, then
        # execute the resulting registered workflow.
        version = uuid.uuid4().hex
        flyte_wf = remote.register_script(
            wf,
            version=version,
            source_path=here,
            module_name="solution",
            default_launch_plan=True,
        )
        ex = remote.execute(
            flyte_wf,
            inputs={"X_train": X_train, "y_train": y_train, "X_test": X_test},
            wait=True,
        )

        predictions = ex.outputs["o0"]
    else:
        predictions = wf(X_train=X_train, y_train=y_train, X_test=X_test)

    result = {"predictions": [int(p) for p in predictions]}
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))


if __name__ == "__main__":
    main()
