# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
import json
import os

import flyte

env = flyte.TaskEnvironment(name="etl_sensor_readings_t1")


@env.task
async def clean(readings: list[int]) -> list[int]:
    """Drop every negative reading (keep values >= 0)."""
    return [r for r in readings if r >= 0]


@env.task
async def aggregate(xs: list[int]) -> tuple[int, float]:
    """Compute how many readings were kept and their arithmetic mean."""
    count = len(xs)
    mean = round(sum(xs) / count, 3) if count else 0.0
    return count, mean


@env.task
async def main(readings: list[int]) -> tuple[int, float]:
    kept = await clean(readings)
    return await aggregate(kept)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    config_path = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")
    if config_path:
        flyte.init_from_config(config_path)
        run = flyte.with_runcontext(mode="remote").run(main, readings=inputs["readings"])
        print(run.name, run.url)
        run.wait()
        count, mean = run.outputs().o0, run.outputs().o1
    else:
        flyte.init()
        count, mean = flyte.run(main, readings=inputs["readings"])

    print(f"TRIAL_OUTPUT_JSON:{json.dumps({'count': count, 'mean': mean})}")
