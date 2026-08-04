# Group B in Flyte v1 — infeasible (that is the result)

The group-B specs are the value-dependent, in-process control-flow patterns v1
cannot express even with `@dynamic`. There is no reference solution because a
correct v1 solution does not exist; the v1 arm should record each as
`infeasible=true`. This file documents *why*, so the harness's expected outcome
is grounded.

`@dynamic` runs Python at runtime only to **build a static sub-graph**, which it
then hands back to the engine to execute. Inside it, a task result is still a
graph Promise, not a real value you can branch on, await, or race. So anything
needing *a decision made from a task's actual output, in-process, that changes
what runs next* is where v1 stops.

- **`oom_retry`** — retries in v1 are declared statically on the graph
  (`@task(retries=N)`), each a fresh identical pod. You cannot catch a live
  `OOMError` from one node and re-launch *that same node* with a larger memory
  envelope as ordinary control flow. `with_overrides` sets resources at compile
  time, not in response to a runtime failure.

- **`circuit_breaker`** — a v1 task Promise is a graph handle, not an awaitable
  future. You cannot feed Promises to `asyncio.wait(FIRST_COMPLETED)`, cancel
  in-flight nodes, or branch on "the 3rd of 10 just failed." `@dynamic`
  materializes the whole sub-graph *before* execution, so it cannot react to
  results as they land.

- **`agent_loop`** — the only unit of recovery in v1 is a task = a pod. A durable
  N-step loop is therefore either one opaque task with no checkpointing (a crash
  restarts from zero) or a pod-per-step explosion. There is no in-process
  checkpointed step (v2's `@flyte.trace`), so the durable loop is not
  expressible.

`@eager` (flytekit) `await`s task outputs as real values and can express some of
this, but it is a separate, heavier, less-mature execution mode outside the
standard `@workflow`/`@dynamic` model the cheatsheet covers — and it does not
give live-future racing or in-process per-call checkpointing. The head-to-head
comparison holds `@eager` out of scope; treat these three as v1-infeasible.
