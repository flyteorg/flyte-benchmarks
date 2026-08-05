# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
import asyncio
import json
import os

import flyte

env = flyte.TaskEnvironment(name="fanout_map")


@env.task
async def sq(x: int) -> int:
    return x * x


@env.task
async def all_squares(xs: list[int]) -> list[int]:
    return await asyncio.gather(*[sq(x) for x in xs])


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)
    xs = inputs["xs"]

    config_path = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")
    if config_path:
        flyte.init_from_config(config_path)
        run = flyte.with_runcontext(mode="remote").run(all_squares, xs=xs)
        print(run.name, run.url)
        run.wait()
        squares = run.outputs().o0
    else:
        flyte.init()
        squares = flyte.run(all_squares, xs=xs)

    print("TRIAL_OUTPUT_JSON:" + json.dumps({"squares": list(squares)}))
