# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52", "scikit-learn>=1.3"]
# ///
"""Reference solution (HELD OUT). Spec `train_classifier`, Flyte v2 — sklearn."""
import json

import flyte

env = flyte.TaskEnvironment(name="train_clf")


@env.task
async def train_predict(X_train: list[list[float]], y_train: list[int],
                        X_test: list[list[float]]) -> list[int]:
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression().fit(X_train, y_train)
    return [int(p) for p in clf.predict(X_test)]


@env.task
async def main(X_train: list[list[float]], y_train: list[int],
               X_test: list[list[float]]) -> dict:
    preds = await train_predict(X_train, y_train, X_test)
    return {"predictions": preds}


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))            # public: no y_test
    flyte.init()
    r = flyte.run(main, **inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps(r.outputs().o0))
