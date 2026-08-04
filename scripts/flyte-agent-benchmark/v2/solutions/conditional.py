# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
"""Reference solution (HELD OUT). Spec `conditional`, Flyte v2 — native if."""
import json

import flyte

env = flyte.TaskEnvironment(name="cond")


@env.task
async def times_two(x: int) -> int:
    return x * 2


@env.task
async def plus_hundred(x: int) -> int:
    return x + 100


@env.task
async def main(value: int, threshold: int) -> dict:
    if value >= threshold:                    # real values — ordinary Python
        return {"result": await times_two(value)}
    return {"result": await plus_hundred(value)}


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))
    flyte.init()
    r = flyte.run(main, **inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps(r.outputs().o0))
