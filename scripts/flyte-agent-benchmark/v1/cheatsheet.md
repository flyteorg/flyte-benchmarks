# Flyte v1 (`flytekit`) authoring cheatsheet

The in-context doc budget for the **v1 arm** (`pip install flytekit`). A
`@workflow` body is *compiled into a DAG*, not executed: a task call returns a
**Promise**, not a real value, so you cannot do plain Python control flow on task
outputs — you use flytekit's DSL (`conditional`, `map_task`, `@dynamic`). Docs:
union.ai/docs/v1/flyte/user-guide.

## Basics — task, workflow, passing outputs

```python
from flytekit import task, workflow

@task
def clean(readings: list[int]) -> list[int]:     # annotations REQUIRED
    return [r for r in readings if r >= 0]

@task
def mean(xs: list[int]) -> float:
    return round(sum(xs) / len(xs), 3)

@workflow
def wf(readings: list[int]) -> float:
    kept = clean(readings=readings)      # keyword args ONLY; kept is a Promise
    return mean(xs=kept)
```

Rules: every param/return type-annotated; inside `@workflow` call tasks with
**keyword arguments only**; a workflow body wires a DAG (no eager execution).
Multiple named outputs via `typing.NamedTuple` (`out.field` access).

## Static fan-out — `map_task`

```python
from flytekit import map_task, task, workflow
@task
def sq(x: int) -> int: return x * x

@workflow
def wf(xs: list[int]) -> list[int]:
    return map_task(sq)(x=xs)            # list[int] in -> list[int] out, parallel
```

Bind extra scalar inputs with `functools.partial(fn, other=...)`; only a single
`@task` can be mapped. Options: `map_task(fn, concurrency=N, min_success_ratio=..)`.

## Conditional — `conditional(...)` DSL

You branch on **Promises**, so you cannot write `if value >= threshold:`. Use:

```python
from flytekit import conditional, task, workflow
@workflow
def wf(value: int, threshold: int) -> int:
    return (
        conditional("pick")
        .if_(value >= threshold)         # bitwise & / | for AND/OR, never and/or
        .then(times_two(x=value))
        .else_()
        .then(plus_hundred(x=value))
    )
```

Must be exhaustive (`.else_().then(...)` or `.fail("msg")`). For a boolean
Promise use `.if_(p.is_true())` / `.is_false()` / `.is_none()`, not `.if_(p)`.

## Data-dependent fan-out — `@dynamic`

When the DAG shape depends on a runtime value, use `@dynamic`: its body runs at
execution time so its *inputs* are concrete Python, and each task call is
compiled into the graph on the fly.

```python
from flytekit import dynamic, task, workflow
@task
def count(seed: int) -> int: return (seed % 5) + 3
@task
def work(i: int) -> int: return i * i

@dynamic
def fan(n: int) -> list[int]:            # n is a real int here
    return [work(i=i) for i in range(n)]

@workflow
def wf(seed: int) -> list[int]:
    return fan(n=count(seed=seed))       # N comes from an upstream task output
```

Inside `@dynamic`, the function inputs are real, but tasks you call still return
Promises (you can't read their values mid-body).

## Resources, retries, `with_overrides`

Declared **statically** on the task / call-site — the control plane, not your
Python, orchestrates re-execution, so retries must be known at registration time.

```python
import datetime
from flytekit import task, Resources
@task(requests=Resources(cpu="1", mem="256Mi"),
      limits=Resources(cpu="2", mem="1Gi"),
      retries=3, timeout=datetime.timedelta(minutes=10))
def heavy(x: list[int]) -> int: ...

@workflow
def wf(x: list[int]) -> int:
    return heavy(x=x).with_overrides(limits=Resources(mem="2Gi"))
```

`retries: int` (fresh pod per attempt). There is **no** way to catch a live
failure (e.g. OOM) from one node and re-run *that* node with more memory as
control flow — the retry budget is static graph metadata. `@eager` (async,
`await` gives real values) exists for value-dependent flow but is heavier/newer;
reach for `@dynamic` first for runtime fan-out.

## Caching

```python
from flytekit import task, Cache
@task(cache=Cache(version="1.0"))        # or legacy: cache=True, cache_version="1.0"
def sq(n: int) -> int: return n * n
```

Bump the version string to invalidate. `Cache(...)`: `version`, `serialize`,
`ignored_inputs`, `salt`.

## Running

```bash
pyflyte run --remote script.py wf --readings '[1,-2,3]'   # register + run remotely
pyflyte run script.py wf --readings '[1,-2,3]'            # drop --remote to run locally
```

`script.py` = file, `wf` = the `@workflow` name, then `--<input>` per workflow
input (lists/dicts as JSON strings). Programmatic:

```python
from flytekit import FlyteRemote
from flytekit.configuration import Config
remote = FlyteRemote(Config.auto(), default_project="flytesnacks",
                     default_domain="development")
wf = remote.register_script(...)          # or remote.fetch_workflow(...)
ex = remote.execute(wf, inputs={"readings": [1, -2, 3]})
remote.wait(ex)                           # ex.outputs for results
```

## Gotchas — where authoring trips

- **Task outputs are Promises in a `@workflow`.** You cannot `if`/`for`/`len()`
  on them, call arbitrary methods (`p.upper()`), or index (except NamedTuple
  field access). Anything needing the real value must be **inside a task**.
- Branch via `conditional` (§conditional), not `if`; fan out by runtime N via
  `@dynamic` (§dynamic), not a plain `for` in a `@workflow`.
- `conditional` needs bitwise `&`/`|` and `.is_true()`, and must be exhaustive.
- `map_task` wraps a single `@task` only; non-mapped inputs need `partial`.
- Keyword-only task calls; every input/output must be type-annotated.
