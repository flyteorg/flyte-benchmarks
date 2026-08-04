# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
"""Reference solution (HELD OUT — never show to the agent under test).

Spec `etl`, Flyte v2. Local execution: `flyte.init()` (bare, no config/cluster)
then `flyte.run(...).outputs().o0`. Prints TRIAL_OUTPUT_JSON for oracle.py.
"""
import json

import flyte

env = flyte.TaskEnvironment(name="etl")


@env.task
async def clean(readings: list[int]) -> list[int]:
    return [r for r in readings if r >= 0]


@env.task
async def aggregate(xs: list[int]) -> dict:
    c = len(xs)
    return {"count": c, "mean": round(sum(xs) / c, 3) if c else 0.0}


@env.task
async def main(readings: list[int]) -> dict:
    kept = await clean(readings)              # real list[int]
    return await aggregate(kept)


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))
    flyte.init()                              # local, in-process
    r = flyte.run(main, **inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps(r.outputs().o0))
