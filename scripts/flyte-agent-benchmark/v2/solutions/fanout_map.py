# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
"""Reference solution (HELD OUT). Spec `fanout_map`, Flyte v2 — asyncio.gather."""
import asyncio
import json

import flyte

env = flyte.TaskEnvironment(name="fanout")


@env.task
async def sq(x: int) -> int:
    return x * x


@env.task
async def main(xs: list[int]) -> dict:
    squares = await asyncio.gather(*[sq(x) for x in xs])   # parallel, order preserved
    return {"squares": list(squares)}


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))
    flyte.init()
    r = flyte.run(main, **inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps(r.outputs().o0))
