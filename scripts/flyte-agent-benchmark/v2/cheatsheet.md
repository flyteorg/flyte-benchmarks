# Flyte v2 (`flyte` SDK) authoring cheatsheet

The in-context doc budget for the **v2 arm**. This is the new `flyte` package
(`pip install flyte`), not `flytekit`. Tasks are ordinary async Python; a task's
output is a **real materialized value**, so you use native `for` / `if` /
`try`/`except` / `await`. Docs: union.ai/docs/v2/flyte/user-guide.

## Basics — environment, tasks, passing outputs

```python
import flyte

env = flyte.TaskEnvironment(name="demo")   # a task lives on an environment

@env.task
async def clean(readings: list[int]) -> list[int]:   # annotations REQUIRED
    return [r for r in readings if r >= 0]

@env.task
async def mean(xs: list[int]) -> float:
    return round(sum(xs) / len(xs), 3)

@env.task
async def main(readings: list[int]) -> float:
    kept = await clean(readings)     # kept is a real list[int]
    return await mean(kept)
```

The "workflow" is just a task that awaits other tasks. Sync `def` tasks work
too (call directly, no `await`); from an async task call a sync task with
`.aio()`.

## Static fan-out (parallel over a list)

```python
import asyncio
@env.task
async def sq(x: int) -> int: return x * x

@env.task
async def all_squares(xs: list[int]) -> list[int]:
    return await asyncio.gather(*[sq(x) for x in xs])   # task calls are awaitables
```

`flyte.map(fn, items, concurrency=N)` is an alternative (returns a generator —
wrap in `list()`; async form `flyte.map.aio`).

## Conditional — native `if`

```python
@env.task
async def choose(value: int, threshold: int) -> int:
    if value >= threshold:            # real values, ordinary Python
        return await times_two(value)
    return await plus_hundred(value)
```

## Data-dependent fan-out — native `for`

```python
@env.task
async def main(seed: int) -> int:
    n = await count(seed)                                  # real int from a task
    parts = await asyncio.gather(*[work(i) for i in range(n)])
    return sum(parts)
```

## Resources, retries, `.override(...)`, typed errors

```python
import flyte, flyte.errors
env = flyte.TaskEnvironment(name="w",
        resources=flyte.Resources(cpu=1, memory="256Mi"))  # tuples ok: memory=("256Mi","1Gi")

@env.task(retries=3)                 # declarative: fresh pod per attempt
async def flaky() -> str: ...

@env.task
async def worker(allotted_mb: int, required_mb: int) -> int:
    if allotted_mb < required_mb:
        raise flyte.errors.OOMError("out of memory")
    return allotted_mb

@env.task
async def drive(tiers: list[int], required_mb: int) -> int:
    for mb in tiers:                                   # escalate on OOM
        try:
            return await worker.override(              # .override(...) returns a callable
                resources=flyte.Resources(memory=f"{mb}Mi"))(mb, required_mb)
        except flyte.errors.OOMError:
            continue
    raise RuntimeError("OOM at max tier")
```

`flyte.errors`: `OOMError`, `NonRecoverableError`, `RuntimeUserError` (`.code`
holds the original exception name). `flyte.RetryStrategy(count=, backoff=flyte.Backoff(...))`
for backoff. `@env.task` kwargs: `retries=`, `timeout=`, `cache=`, `secrets=`.

## Racing live tasks / circuit-breaker (asyncio)

Task calls are awaitable futures — wrap with `asyncio.create_task`, race with
`asyncio.wait(..., FIRST_COMPLETED)`, `.cancel()` the losers:

```python
@env.task
async def race(delays: list[float], fail: list[int], max_failures: int) -> int:
    tasks = {asyncio.create_task(cand(i, delays[i], i in fail)): i for i in range(len(delays))}
    failures, pending = 0, set(tasks)
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for t in done:
            if t.exception():
                failures += 1
                if failures > max_failures:
                    for p in pending: p.cancel()
                    return -1
            else:
                for p in pending: p.cancel()
                return tasks[t]
    return -1
```

## Durable checkpointed sub-calls — `@flyte.trace`

Decorate a plain async helper so each call is a recorded, replayable step (crash
resumes from the last completed call). Basis for durable tool/agent loops:

```python
@flyte.trace
async def add(acc: int, k: int) -> int: return acc + k
@flyte.trace
async def mul(acc: int, k: int) -> int: return acc * k

@env.task
async def run_program(start: int, program: list) -> int:
    acc = start
    for op, arg in program:                       # each tool call is checkpointed
        acc = await (add(acc, arg) if op == "add" else mul(acc, arg))
    return acc
```

`flyte.ReusePolicy(replicas=, concurrency=)` on the env keeps warm containers so
many small calls skip cold start (needs `unionai-reuse` in the image). Full
agents: `from flyte.ai.agents import Agent` (`Agent(name=, model=, tools=[...],
max_turns=)`, `await agent.run.aio(...)`).

## Running

Config: `flyte.init_from_config("config.yaml")` (path arg) or `init_from_config()`
to auto-discover (`./config.yaml`, `~/.flyte/config.yaml`, `$FLYTE_CONFIG`). The
first call opens a browser for PKCE login; `flyte whoami` verifies identity.

```python
if __name__ == "__main__":
    flyte.init_from_config("config.yaml")          # remote endpoint from the config
    run = flyte.with_runcontext(mode="remote").run(main, readings=[1, -2, 3])
    print(run.name, run.url)
    run.wait()                                     # remote runs are async
    print(run.outputs().o0)                        # single return value
```

`.run` in remote mode **auto-registers** the task envs (no `flyte.deploy` needed
for a one-shot). `mode=` is a keyword. LOCAL: bare `flyte.init()` then
`flyte.run(main, ...)` (blocks; no `.wait()`). CLI: `flyte run file.py main
--readings '[1,-2,3]'` (`--local` for local).

## Caching

```python
@env.task(cache="auto")                            # or flyte.Cache(behavior="auto")
async def t(data: str) -> str: ...
# behavior: "auto" | "override" (+version_override=) | "disable"
```

## Gotchas

- `.override(...)` returns a **new callable** — call it: `t.override(...)(args)`.
- A forgotten `await` yields a coroutine, not a value.
- `mode="remote"` is keyword; caching behaviors are `auto|override|disable`.
