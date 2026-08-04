# /// script
# requires-python = ">=3.12"
# dependencies = ["flyte>=2.0.0b52"]
# ///
"""Reference solution (HELD OUT). Spec `circuit_breaker`, Flyte v2 — live race.

Task calls are awaitable futures, so we race them with asyncio: first success
wins (cancel the losers); if more than max_failures fail first, open the circuit
(return -1). Within a single completed batch we process in delay order so the
first-in-time event decides, matching the oracle's time-ordered reference.
"""
import asyncio
import json

import flyte

env = flyte.TaskEnvironment(name="cb")


@env.task
async def candidate(idx: int, delay: float, fails: bool) -> int:
    await asyncio.sleep(delay)
    if fails:
        raise RuntimeError(f"candidate {idx} failed")
    return idx


@env.task
async def race(delays: list[float], fail_indices: list[int], max_failures: int) -> int:
    failset = set(fail_indices)
    tasks = {asyncio.create_task(candidate(i, delays[i], i in failset)): i
             for i in range(len(delays))}
    pending, failures, winner = set(tasks), 0, -1
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        decided = False
        for t in sorted(done, key=lambda t: delays[tasks[t]]):   # time order
            if t.exception() is not None:
                failures += 1
                if failures > max_failures:
                    winner, decided = -1, True
                    break
            else:
                winner, decided = tasks[t], True
                break
        if decided:
            break
    for p in pending:                          # cancel the losers
        p.cancel()
    return winner


@env.task
async def main(delays: list[float], fail_indices: list[int], max_failures: int) -> dict:
    return {"winner": await race(delays, fail_indices, max_failures)}


if __name__ == "__main__":
    import os
    inp = json.load(open("inputs.json"))
    cfg = os.getenv("FLYTE_AGENT_BENCH_CONFIG")            # set -> run on the cluster
    if cfg:
        flyte.init_from_config(cfg)
        run = flyte.with_runcontext(mode="remote").run(main, **inp)
        run.wait()                                         # remote runs are async
    else:
        flyte.init()                                       # local smoke, no cluster
        run = flyte.run(main, **inp)
    print("TRIAL_OUTPUT_JSON:" + json.dumps(run.outputs().o0))
