# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
"""Reference solution (HELD OUT). Spec `agent_loop`, Flyte v2 — durable tool loop.

Each tool call is a @flyte.trace step: a checkpointed, replayable span, so a
crash mid-loop resumes from the last completed tool call rather than restarting.
(Swap the trace tools for `flyte.ai.agents.Agent` + an LLM to get the full
agentic version; the durable-loop mechanics are identical.)
"""
import json

import flyte

env = flyte.TaskEnvironment(name="agent")


@flyte.trace
async def add(acc: int, k: int) -> int:
    return acc + k


@flyte.trace
async def mul(acc: int, k: int) -> int:
    return acc * k


@env.task
async def run_program(start: int, program: list) -> int:
    acc = start
    for op, arg in program:                    # each tool call is checkpointed
        acc = await (add(acc, arg) if op == "add" else mul(acc, arg))
    return acc


@env.task
async def main(start: int, program: list) -> dict:
    return {"answer": await run_program(start, program)}


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))
    flyte.init()
    r = flyte.run(main, **inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps(r.outputs().o0))
