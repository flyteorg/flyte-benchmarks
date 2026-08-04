# /// script
# requires-python = ">=3.12"
# dependencies = ["flytekit>=1.13"]
# ///
"""Reference solution (HELD OUT). Spec `fanout_map`, Flyte v1 — map_task."""
import json

from flytekit import map_task, task, workflow


@task
def sq(x: int) -> int:
    return x * x


@workflow
def wf(xs: list[int]) -> list[int]:
    return map_task(sq)(x=xs)


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
        result = {"squares": list(out["o0"])}
    else:                                                 # local smoke, no cluster
        result = {"squares": list(wf(**inp))}
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))
