# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["flytekit>=1.13"]
# ///
"""Flyte v1 (flytekit) solution for the dynamic_fanout spec.

Stage 1: `count` reads `seed` and returns N = (seed % 5) + 3.
Stage 2: N is only known at runtime, so the fan-out lives inside a `@dynamic`
workflow (its body runs at execution time with a real int `n`). Each of the
N leaves is a `work(i)` task returning i*i; a downstream `total_sum` task
sums the Promises returned by the dynamic (you cannot `sum()` Promises
inside a @workflow).

Reads seed from inputs.json in the cwd, submits + waits on the configured
Flyte cluster (falls back to a local run if FLYTE_AGENT_BENCH_CONFIG is not
set), and prints one line: TRIAL_OUTPUT_JSON:{"n": ..., "total": ...}
"""
import json
import os
from typing import NamedTuple

from flytekit import dynamic, task, workflow

Out = NamedTuple("Out", [("n", int), ("total", int)])


@task
def dynfan_count(seed: int) -> int:
    return (seed % 5) + 3


@task
def dynfan_work(i: int) -> int:
    return i * i


@task
def dynfan_total_sum(xs: list[int]) -> int:
    return sum(xs)


@dynamic
def dynfan_fan(n: int) -> list[int]:
    return [dynfan_work(i=i) for i in range(n)]


@workflow
def dynfan_wf(seed: int) -> Out:
    n = dynfan_count(seed=seed)
    results = dynfan_fan(n=n)
    total = dynfan_total_sum(xs=results)
    return Out(n=n, total=total)


def main() -> None:
    with open("inputs.json") as f:
        inputs = json.load(f)
    seed = inputs["seed"]

    config_path = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")

    if config_path:
        import uuid

        from flytekit.configuration import Config, ImageConfig
        from flytekit.remote import FlyteRemote

        remote = FlyteRemote(
            Config.auto(config_file=config_path),
            default_project="flytesnacks",
            default_domain="development",
        )
        # Explicit, fresh version so this run always registers/executes THIS
        # code, instead of accidentally matching an older same-named entity
        # (e.g. from a previous trial) via version=None ("latest") lookup.
        version = "dynfan" + uuid.uuid4().hex[:12]
        # register_script fast-packages this file's source and uploads it, so
        # the default flytekit image can import `solution` at task run time
        # (a plain remote.execute() of a local entity assumes the code is
        # already baked into the image, which it isn't here).
        source_path = os.path.dirname(os.path.abspath(__file__))
        registered_wf = remote.register_script(
            dynfan_wf,
            image_config=ImageConfig.auto_default_image(),
            version=version,
            source_path=source_path,
            module_name="solution",
        )
        ex = remote.execute(registered_wf, inputs={"seed": seed}, wait=True)
        n = ex.outputs["n"]
        total = ex.outputs["total"]
    else:
        out = dynfan_wf(seed=seed)
        n = out.n
        total = out.total

    print(f"TRIAL_OUTPUT_JSON:{json.dumps({'n': n, 'total': total})}")


if __name__ == "__main__":
    main()
