# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
import asyncio
import json
from pathlib import Path

import flyte

env = flyte.TaskEnvironment(name="circuit_breaker")


async def cand(i: int, delay: float, should_fail: bool) -> int:
    # A plain local coroutine (not a separate remote @env.task): candidates
    # race purely on their asyncio.sleep timing. Making each candidate its
    # own remote Flyte task would let cluster scheduling/cold-start jitter
    # dominate the small delay deltas and scramble the intended winner.
    await asyncio.sleep(delay)
    if should_fail:
        raise RuntimeError(f"task {i} failed")
    return i


@env.task
async def race(delays: list[float], fail: list[int], max_failures: int) -> int:
    tasks = {
        asyncio.create_task(cand(i, delays[i], i in fail)): i
        for i in range(len(delays))
    }
    failures, pending = 0, set(tasks)
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

        # If any task in this completed batch succeeded, it wins immediately -
        # cancel every other task (pending ones and any other finishers in the
        # same batch) and return its index.
        succeeded = None
        for t in done:
            if t.exception() is None:
                succeeded = t
                break

        if succeeded is not None:
            for p in pending:
                p.cancel()
            for t in done:
                if t is not succeeded:
                    t.exception()  # consume to avoid "exception never retrieved"
            return tasks[succeeded]

        # No success in this batch - count the failures and check the circuit.
        failures += len(done)
        if failures > max_failures:
            for p in pending:
                p.cancel()
            return -1

    return -1


@env.task
async def main(delays: list[float], fail_indices: list[int], max_failures: int) -> int:
    return await race(delays, fail_indices, max_failures)


if __name__ == "__main__":
    import os

    inputs = json.loads((Path(__file__).parent / "inputs.json").read_text())

    config_path = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")
    if config_path:
        flyte.init_from_config(config_path)
        run = flyte.with_runcontext(mode="remote").run(
            main,
            delays=inputs["delays"],
            fail_indices=inputs["fail_indices"],
            max_failures=inputs["max_failures"],
        )
        print(run.name, run.url)
        run.wait()
        winner = run.outputs().o0
    else:
        flyte.init()
        winner = flyte.run(
            main,
            delays=inputs["delays"],
            fail_indices=inputs["fail_indices"],
            max_failures=inputs["max_failures"],
        )

    print(f"TRIAL_OUTPUT_JSON:{json.dumps({'winner': winner})}")
