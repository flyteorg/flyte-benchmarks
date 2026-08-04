# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
import asyncio
import json
import os

import flyte

env = flyte.TaskEnvironment(name="dynamic_fanout")


@env.task
async def count(seed: int) -> int:
    return (seed % 5) + 3


@env.task
async def square(i: int) -> int:
    return i * i


@env.task
async def main(seed: int) -> dict:
    n = await count(seed)
    parts = await asyncio.gather(*[square(i) for i in range(n)])
    total = sum(parts)
    return {"n": n, "total": total}


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    config_path = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")
    if config_path:
        flyte.init_from_config(config_path)
        run = flyte.with_runcontext(mode="remote").run(main, seed=inputs["seed"])
        print(run.name, run.url)
        run.wait()
        result = run.outputs().o0
    else:
        flyte.init()
        result = flyte.run(main, seed=inputs["seed"])

    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))
