import asyncio
import json
import os

import flyte
import flyte.errors

env = flyte.TaskEnvironment(name="circuit_breaker")


async def cand(i: int, delay: float, should_fail: bool) -> int:
    # Plain async coroutine (not @env.task): each "task" here is an
    # in-process asyncio task racing against its siblings. Spawning each
    # candidate as a separate remote Flyte task would add multi-second pod
    # scheduling overhead that swamps the sub-second delays being raced.
    await asyncio.sleep(delay)
    if should_fail:
        raise RuntimeError(f"task {i} failed")
    return i


@env.task
async def race(delays: list[float], fail_indices: list[int], max_failures: int) -> int:
    fail_set = set(fail_indices)
    tasks = {
        asyncio.create_task(cand(i, delays[i], i in fail_set)): i
        for i in range(len(delays))
    }
    failures = 0
    pending = set(tasks)
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for t in done:
            if t.exception():
                failures += 1
                if failures > max_failures:
                    for p in pending:
                        p.cancel()
                    return -1
            else:
                for p in pending:
                    p.cancel()
                return tasks[t]
    return -1


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    config_path = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")
    if config_path:
        flyte.init_from_config(config_path)
        run = flyte.with_runcontext(mode="remote").run(
            race,
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
            race,
            delays=inputs["delays"],
            fail_indices=inputs["fail_indices"],
            max_failures=inputs["max_failures"],
        )

    print("TRIAL_OUTPUT_JSON:" + json.dumps({"winner": winner}))
