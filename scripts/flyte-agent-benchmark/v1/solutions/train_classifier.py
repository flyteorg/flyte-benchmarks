# /// script
# requires-python = ">=3.12"
# dependencies = ["flytekit>=1.13", "scikit-learn>=1.3"]
# ///
"""Reference solution (HELD OUT). Spec `train_classifier`, Flyte v1 — sklearn."""
import json

from flytekit import task, workflow


@task
def train_predict(X_train: list[list[float]], y_train: list[int],
                  X_test: list[list[float]]) -> list[int]:
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression().fit(X_train, y_train)
    return [int(p) for p in clf.predict(X_test)]


@workflow
def wf(X_train: list[list[float]], y_train: list[int],
       X_test: list[list[float]]) -> list[int]:
    return train_predict(X_train=X_train, y_train=y_train, X_test=X_test)


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))            # public: no y_test
    preds = wf(**inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps({"predictions": [int(p) for p in preds]}))
