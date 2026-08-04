# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["flytekit"]
# ///
"""Flyte v1 (flytekit) ETL pipeline: drop negative readings, then compute
count + mean of the kept readings. Two-step DAG: clean -> aggregate."""
import hashlib
import json
import os
from typing import NamedTuple

from flytekit import task, workflow


class Stats(NamedTuple):
    count: int
    mean: float


@task
def clean(readings: list[int]) -> list[int]:
    return [r for r in readings if r >= 0]


@task
def aggregate(xs: list[int]) -> Stats:
    n = len(xs)
    m = round(sum(xs) / n, 3)
    return Stats(count=n, mean=m)


@workflow
def wf(readings: list[int]) -> Stats:
    kept = clean(readings=readings)
    return aggregate(xs=kept)


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    readings = inputs["readings"]
    config_file = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")

    if config_file:
        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote

        remote = FlyteRemote(
            Config.auto(config_file=config_file),
            default_project="flytesnacks",
            default_domain="development",
            interactive_mode_enabled=True,
        )
        version = hashlib.sha1(open(__file__, "rb").read()).hexdigest()[:20]
        ex = remote.execute(
            wf, inputs={"readings": readings}, version=version, wait=True
        )
        count = ex.outputs["count"]
        mean = ex.outputs["mean"]
    else:
        result = wf(readings=readings)
        count = result.count
        mean = result.mean

    print(f"TRIAL_OUTPUT_JSON:{json.dumps({'count': int(count), 'mean': float(mean)})}")


if __name__ == "__main__":
    main()
