# /// script
# requires-python = ">=3.10"
# dependencies = ["flyte"]
# ///
"""Train a binary classifier and predict a held-out test set, on Flyte v2."""
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
    # Nearest-centroid classifier: compute the mean feature vector for each
    # class from the training data, then assign each test row to whichever
    # centroid is closer (Euclidean distance). No external ML deps needed.
    n_features = len(X_train[0])
    sums: dict[int, list[float]] = {}
    counts: dict[int, int] = {}
    for row, label in zip(X_train, y_train):
        if label not in sums:
            sums[label] = [0.0] * n_features
            counts[label] = 0
        for i, v in enumerate(row):
            sums[label][i] += v
        counts[label] += 1

    centroids = {
        label: [s / counts[label] for s in sums[label]] for label in sums
    }

    predictions: list[int] = []
    for row in X_test:
        best_label = None
        best_dist = None
        for label, centroid in centroids.items():
            dist = sum((a - b) ** 2 for a, b in zip(row, centroid))
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_label = label
        predictions.append(best_label)

    return predictions


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    config_path = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")
    if config_path:
        flyte.init_from_config(config_path)
        run = flyte.with_runcontext(mode="remote").run(
            train_and_predict,
            X_train=inputs["X_train"],
            y_train=inputs["y_train"],
            X_test=inputs["X_test"],
        )
        print(run.name, run.url)
        run.wait()
        predictions = run.outputs().o0
    else:
        flyte.init()
        predictions = flyte.run(
            train_and_predict,
            X_train=inputs["X_train"],
            y_train=inputs["y_train"],
            X_test=inputs["X_test"],
        )

    print("TRIAL_OUTPUT_JSON:" + json.dumps({"predictions": predictions}))
