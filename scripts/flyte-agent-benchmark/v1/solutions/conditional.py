# /// script
# requires-python = ">=3.12"
# dependencies = ["flytekit>=1.13"]
# ///
"""Reference solution (HELD OUT). Spec `conditional`, Flyte v1 — conditional()."""
import json

from flytekit import conditional, task, workflow


@task
def times_two(x: int) -> int:
    return x * 2


@task
def plus_hundred(x: int) -> int:
    return x + 100


@workflow
def wf(value: int, threshold: int) -> int:
    return (
        conditional("pick")
        .if_(value >= threshold)              # branch on Promises, not `if`
        .then(times_two(x=value))
        .else_()
        .then(plus_hundred(x=value))
    )


if __name__ == "__main__":
    import os
    inp = json.load(open("inputs.json"))
    cfg = os.getenv("FLYTE_AGENT_BENCH_CONFIG")            # set -> run on the cluster
    if cfg:                                                # remote: submit + fetch outputs
        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote
        remote = FlyteRemote(Config.auto(config_file=cfg),
                             default_project=os.getenv("FLYTE_BENCH_PROJECT", "flytesnacks"),
                             default_domain=os.getenv("FLYTE_BENCH_DOMAIN", "development"))
        out = remote.execute(wf, inputs=inp, wait=True).outputs   # auto-registers + runs + waits
        result = {"result": out["o0"]}
    else:                                                 # local smoke, no cluster
        result = {"result": wf(**inp)}
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))
