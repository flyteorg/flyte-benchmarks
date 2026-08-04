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
    import os
    inp = json.load(open("inputs.json"))            # public: no y_test
    cfg = os.getenv("FLYTE_AGENT_BENCH_CONFIG")            # set -> run on the cluster
    if cfg:                                                # remote: submit + fetch outputs
        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote
        remote = FlyteRemote(Config.auto(config_file=cfg),
                             default_project=os.getenv("FLYTE_BENCH_PROJECT", "flytesnacks"),
                             default_domain=os.getenv("FLYTE_BENCH_DOMAIN", "development"))
        out = remote.execute(wf, inputs=inp, wait=True).outputs   # auto-registers + runs + waits
        result = {"predictions": [int(p) for p in out["o0"]]}
    else:                                                 # local smoke, no cluster
        result = {"predictions": [int(p) for p in wf(**inp)]}
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))
