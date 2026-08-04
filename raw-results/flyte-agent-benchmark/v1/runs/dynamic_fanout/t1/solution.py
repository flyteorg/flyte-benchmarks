# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["flytekit>=1.13"]
# ///
import json
import os
from typing import NamedTuple

from flytekit import dynamic, task, workflow
from flytekit.configuration import Config
from flytekit.remote import FlyteRemote


class FanoutOutput(NamedTuple):
    n: int
    total: int


@task
def compute_n(seed: int) -> int:
    return (seed % 5) + 3


@task
def square(i: int) -> int:
    return i * i


@task
def sum_list(xs: list[int]) -> int:
    return sum(xs)


@dynamic
def fan(n: int) -> list[int]:
    return [square(i=i) for i in range(n)]


@workflow
def wf(seed: int) -> FanoutOutput:
    n = compute_n(seed=seed)
    results = fan(n=n)
    total = sum_list(xs=results)
    return FanoutOutput(n=n, total=total)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)
    seed = inputs["seed"]

    config_file = os.environ.get("FLYTE_AGENT_BENCH_CONFIG") or os.environ.get("FLYTECTL_CONFIG")
    if config_file:
        remote = FlyteRemote(
            Config.auto(config_file=config_file),
            default_project="flytesnacks",
            default_domain="development",
        )
        import hashlib
        import time

        # @dynamic tasks aren't supported by FlyteRemote's "interactive mode" pickling,
        # and plain remote.execute() (non-interactive) doesn't upload source, so the
        # pod can't import the module. Fast-register the script explicitly instead.
        version = hashlib.sha1(f"dynamic_fanout-{time.time()}".encode()).hexdigest()[:16]
        registered_wf = remote.register_script(
            wf,
            source_path=here,
            module_name="solution",
            version=version,
        )
        ex = remote.execute(registered_wf, inputs={"seed": seed}, wait=True)
        n = ex.outputs["n"]
        total = ex.outputs["total"]
    else:
        result = wf(seed=seed)
        n = result.n
        total = result.total

    print(f"TRIAL_OUTPUT_JSON:{json.dumps({'n': int(n), 'total': int(total)})}")
