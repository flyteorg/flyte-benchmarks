# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["flytekit>=1.13"]
# ///
import json
import os
import typing

from flytekit import task, workflow

Agg = typing.NamedTuple("Agg", count=int, mean=float)


@task
def clean(readings: list[int]) -> list[int]:
    return [r for r in readings if r >= 0]


@task
def aggregate(xs: list[int]) -> Agg:
    n = len(xs)
    m = round(sum(xs) / n, 3) if n > 0 else 0.0
    return Agg(count=n, mean=m)


@workflow
def wf(readings: list[int]) -> Agg:
    kept = clean(readings=readings)
    return aggregate(xs=kept)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    config_file = os.environ.get("FLYTE_AGENT_BENCH_CONFIG") or os.environ.get("FLYTECTL_CONFIG")

    if config_file:
        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote

        remote = FlyteRemote(
            Config.auto(config_file=config_file),
            default_project="flytesnacks",
            default_domain="development",
        )
        ex = remote.execute(wf, inputs=inputs, wait=True)
        count = ex.outputs["count"]
        mean = ex.outputs["mean"]
    else:
        result = wf(readings=inputs["readings"])
        count = result.count
        mean = result.mean

    print(f"TRIAL_OUTPUT_JSON:{json.dumps({'count': int(count), 'mean': float(mean)})}")


if __name__ == "__main__":
    main()
