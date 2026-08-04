# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
"""oom_retry — Flyte v2 solution.

Worker task models an OOM: given allotted_mb and (hidden-from-logic) required_mb,
it raises flyte.errors.OOMError if allotted_mb < required_mb, else returns
allotted_mb. The control task starts at the smallest tier and, on OOM, re-runs
the SAME worker step with the next larger tier -- overriding its memory
resource request to that tier -- until it succeeds, returning the tier that
worked.
"""
import json
import os

import flyte
import flyte.errors

env = flyte.TaskEnvironment(
    name="oom_retry",
    resources=flyte.Resources(cpu=1, memory="256Mi"),
)


@env.task
async def worker(allotted_mb: int, required_mb: int) -> int:
    if allotted_mb < required_mb:
        raise flyte.errors.OOMError("OOMError", "out of memory")
    return allotted_mb


@env.task
async def drive(tiers: list[int], required_mb: int) -> int:
    for mb in tiers:
        try:
            return await worker.override(
                resources=flyte.Resources(memory=f"{mb}Mi")
            )(mb, required_mb)
        except flyte.errors.OOMError:
            continue
    raise RuntimeError("OOM at max tier")


if __name__ == "__main__":
    with open("inputs.json") as f:
        inputs = json.load(f)

    config_path = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")
    if config_path:
        flyte.init_from_config(config_path)
        run = flyte.with_runcontext(mode="remote").run(
            drive, tiers=inputs["tiers"], required_mb=inputs["required_mb"]
        )
        print(run.name, run.url)
        run.wait()
        succeeded_at_mb = run.outputs().o0
    else:
        flyte.init()
        succeeded_at_mb = flyte.run(
            drive, tiers=inputs["tiers"], required_mb=inputs["required_mb"]
        )

    print(f"TRIAL_OUTPUT_JSON:{json.dumps({'succeeded_at_mb': succeeded_at_mb})}")
