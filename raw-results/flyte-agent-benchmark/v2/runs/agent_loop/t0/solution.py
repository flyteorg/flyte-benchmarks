# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
import json
import os

import flyte

env = flyte.TaskEnvironment(name="agent_loop")


@flyte.trace
async def add(acc: int, k: int) -> int:
    return acc + k


@flyte.trace
async def mul(acc: int, k: int) -> int:
    return acc * k


@env.task
async def run_program(start: int, program: list) -> int:
    acc = start
    for op, arg in program:  # each tool call is a checkpointed step
        acc = await (add(acc, arg) if op == "add" else mul(acc, arg))
    return acc


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    config_path = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")
    if config_path:
        flyte.init_from_config(config_path)
        run = flyte.with_runcontext(mode="remote").run(
            run_program, start=inputs["start"], program=inputs["program"]
        )
        print(run.name, run.url)
        run.wait()
        answer = run.outputs().o0
    else:
        flyte.init()
        answer = flyte.run(
            run_program, start=inputs["start"], program=inputs["program"]
        )

    print(f"TRIAL_OUTPUT_JSON:{json.dumps({'answer': answer})}")
