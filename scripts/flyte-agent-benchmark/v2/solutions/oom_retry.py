# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
"""Reference solution (HELD OUT). Spec `oom_retry`, Flyte v2 — catch OOM, escalate.

Catch the failure, re-run the SAME step with a larger memory tier (and override
its resources to match) until it succeeds. Local caveat: when a child task's
`OOMError` crosses the task boundary and is caught in the parent, the local
controller re-wraps it as `RuntimeUserError`, so we catch both — that keeps the
solution portable between local smoke runs and a real cluster (where an actual
kernel OOM-kill surfaces as `OOMError`). This pattern is best graded remotely.
"""
import json

import flyte
import flyte.errors

env = flyte.TaskEnvironment(name="oom", resources=flyte.Resources(cpu=1, memory="256Mi"))


@env.task
async def worker(allotted_mb: int, required_mb: int) -> int:
    # models an OOM: fails unless it was given enough memory.
    if allotted_mb < required_mb:
        raise flyte.errors.OOMError("out of memory")
    return allotted_mb


@env.task
async def drive(tiers: list[int], required_mb: int) -> int:
    for mb in tiers:                          # smallest -> largest
        try:
            return await worker.override(
                resources=flyte.Resources(memory=f"{mb}Mi"))(mb, required_mb)
        except (flyte.errors.OOMError, flyte.errors.RuntimeUserError):
            continue                          # bump memory, re-run the SAME step
    raise RuntimeError("OOM even at the largest tier")


@env.task
async def main(tiers: list[int], required_mb: int) -> dict:
    return {"succeeded_at_mb": await drive(tiers, required_mb)}


if __name__ == "__main__":
    import os
    inp = json.load(open("inputs.json"))
    cfg = os.getenv("FLYTE_AGENT_BENCH_CONFIG")            # set -> run on the cluster
    if cfg:
        flyte.init_from_config(cfg)
        run = flyte.with_runcontext(mode="remote").run(main, **inp)
        run.wait()                                         # remote runs are async
    else:
        flyte.init()                                       # local smoke, no cluster
        run = flyte.run(main, **inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps(run.outputs().o0))
