# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
import json
import os

import flyte

env = flyte.TaskEnvironment(name="train_classifier")


@env.task
async def train_and_predict(
    X_train: list[list[float]],
    y_train: list[int],
    X_test: list[list[float]],
) -> list[int]:
    # Nearest-centroid classifier: for each class, compute the mean feature
    # vector over its training rows, then assign each test row to the class
    # whose centroid it is closest to (squared Euclidean distance).
    classes = sorted(set(y_train))
    dim = len(X_train[0])

    centroids: dict[int, list[float]] = {}
    for c in classes:
        rows = [x for x, y in zip(X_train, y_train) if y == c]
        n = len(rows)
        centroids[c] = [sum(row[i] for row in rows) / n for i in range(dim)]

    def sq_dist(a: list[float], b: list[float]) -> float:
        return sum((ai - bi) ** 2 for ai, bi in zip(a, b))

    predictions: list[int] = []
    for row in X_test:
        best_class = min(classes, key=lambda c: sq_dist(row, centroids[c]))
        predictions.append(int(best_class))
    return predictions


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    X_train = [[float(v) for v in row] for row in inputs["X_train"]]
    y_train = [int(v) for v in inputs["y_train"]]
    X_test = [[float(v) for v in row] for row in inputs["X_test"]]

    config_path = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")
    if config_path:
        flyte.init_from_config(config_path)
        run = flyte.with_runcontext(mode="remote").run(
            train_and_predict, X_train=X_train, y_train=y_train, X_test=X_test
        )
        print(run.name, run.url)
        run.wait()
        predictions = run.outputs().o0
    else:
        flyte.init()
        predictions = flyte.run(
            train_and_predict, X_train=X_train, y_train=y_train, X_test=X_test
        )

    output = {"predictions": [int(p) for p in predictions]}
    print(f"TRIAL_OUTPUT_JSON:{json.dumps(output)}")
