# /// script
# requires-python = "==3.12.*"
# dependencies = ["flytekit>=1.13"]
# ///
import json
import os

from flytekit import task, workflow


@task
def train_predict(
    X_train: list[list[float]], y_train: list[int], X_test: list[list[float]]
) -> list[int]:
    # Nearest-centroid classifier (pure python, no extra deps needed on the
    # remote image): fit one centroid per class, predict by closer centroid.
    dim = len(X_train[0])
    sums = {0: [0.0] * dim, 1: [0.0] * dim}
    counts = {0: 0, 1: 0}
    for x, y in zip(X_train, y_train):
        counts[y] += 1
        for i in range(dim):
            sums[y][i] += x[i]
    centroids = {
        c: [sums[c][i] / counts[c] for i in range(dim)] for c in (0, 1)
    }

    preds: list[int] = []
    for x in X_test:
        d0 = sum((x[i] - centroids[0][i]) ** 2 for i in range(dim))
        d1 = sum((x[i] - centroids[1][i]) ** 2 for i in range(dim))
        preds.append(0 if d0 <= d1 else 1)
    return preds


@workflow
def wf(
    X_train: list[list[float]], y_train: list[int], X_test: list[list[float]]
) -> list[int]:
    return train_predict(X_train=X_train, y_train=y_train, X_test=X_test)


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
        import uuid

        remote = FlyteRemote(
            Config.auto(config_file=config_file),
            default_project="flytesnacks",
            default_domain="development",
            interactive_mode_enabled=True,
        )
        version = uuid.uuid4().hex
        ex = remote.execute(
            wf,
            inputs={"X_train": X_train, "y_train": y_train, "X_test": X_test},
            wait=True,
            version=version,
        )
        predictions = ex.outputs["o0"]
    else:
        predictions = wf(X_train=X_train, y_train=y_train, X_test=X_test)

    result = {"predictions": [int(p) for p in predictions]}
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))


if __name__ == "__main__":
    main()
