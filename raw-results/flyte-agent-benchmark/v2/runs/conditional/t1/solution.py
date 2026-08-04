# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
import json
import os

import flyte

env = flyte.TaskEnvironment(name="conditional_demo")


@env.task
async def times_two(value: int) -> int:
    return value * 2


@env.task
async def plus_hundred(value: int) -> int:
    return value + 100


@env.task
async def choose(value: int, threshold: int) -> int:
    if value >= threshold:
        return await times_two(value)
    return await plus_hundred(value)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    config_path = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")
    if config_path:
        flyte.init_from_config(config_path)
        run = flyte.with_runcontext(mode="remote").run(
            choose, value=inputs["value"], threshold=inputs["threshold"]
        )
        print(run.name, run.url)
        run.wait()
        result = run.outputs().o0
    else:
        flyte.init()
        result = flyte.run(
            choose, value=inputs["value"], threshold=inputs["threshold"]
        )

    print(f"TRIAL_OUTPUT_JSON:{json.dumps({'result': result})}")
