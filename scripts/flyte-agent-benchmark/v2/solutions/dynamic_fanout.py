# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
"""Reference solution (HELD OUT). Spec `dynamic_fanout`, Flyte v2 — native for."""
import asyncio
import json

import flyte

env = flyte.TaskEnvironment(name="dyn")


@env.task
async def count(seed: int) -> int:
    return (seed % 5) + 3


@env.task
async def work(i: int) -> int:
    return i * i


@env.task
async def main(seed: int) -> dict:
    n = await count(seed)                     # real int; width known at runtime
    parts = await asyncio.gather(*[work(i) for i in range(n)])
    return {"n": n, "total": sum(parts)}


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))
    flyte.init()
    r = flyte.run(main, **inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps(r.outputs().o0))
