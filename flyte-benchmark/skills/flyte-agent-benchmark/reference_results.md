# Reference results

Numbers from a real head-to-head run of **both arms** — every trial ran a
subagent end-to-end against the live cluster at `development.uniondemo.run`
(project `flytesnacks`, domain `development`), through the actual `oracle.py`
grader, no simulation. Raw output — every `solution.py`, `inputs.json`,
`run.log`, `agent_results.jsonl`, and chart — is checked into
[`raw-results/flyte-agent-benchmark/`](../../../raw-results/flyte-agent-benchmark/):
[`v1/`](../../../raw-results/flyte-agent-benchmark/v1/),
[`v2/`](../../../raw-results/flyte-agent-benchmark/v2/), and the combined
[`agent_results_v1_v2.jsonl`](../../../raw-results/flyte-agent-benchmark/agent_results_v1_v2.jsonl)
used for the head-to-head table below.

**Run date:** 2026-08-04 (both arms, same day). **Model:** claude-sonnet-5
(session default, no override, held fixed across both arms). **Trials:** 2
per spec (seeds 0, 1) × 12 specs × 2 arms = 48. **Turn budget:** 8 run→fix
iterations. The two arms used **identical inputs per (spec, seed)** — v1 and
v2 solved the literal same randomized problem instances, verified by diffing
`inputs.json` across `v1/runs/<spec>/t<seed>/` and `v2/runs/<spec>/t<seed>/`.

## Headline: tokens/iterations to a green run

| group | arm | trials | success | infeasible | tokens→green (mean) | out tokens (mean) | iters→green (mean) | framework-error share |
|---|---|---|---|---|---|---|---|---|
| A — core mechanics | v1 | 10 | 100% | 0 | 71,414 | 667 | 5.0 | 92% |
| A — core mechanics | v2 | 10 | 100% | 0 | 40,622 | 493 | 1.0 | 100% |
| B — v2-only capability | v1 | 6 | **0%** | **6/6** | — | — | — | — |
| B — v2-only capability | v2 | 6 | **100%** | 0 | 52,819 | 582 | 2.0 | 50% |
| C — applied ML | v1 | 8 | 100% | 0 | 75,661 | 911 | 3.5 | 100% |
| C — applied ML | v2 | 8 | 100% | 0 | 41,985 | 677 | 1.0 | — |

**Head-to-head (groups A+C, the token/iteration race both arms can run):**
v2 reaches a green run in **1.78× fewer tokens** (73,301 vs 41,228 mean) and a
**5× lower iteration count** (5.0 vs 1.0 median) — both arms hit 100% success,
so this is a pure efficiency gap, not a capability one. v2's chart:
[`agent_charts_tokens.png`](../../../raw-results/flyte-agent-benchmark/v2/agent_charts_tokens.png);
combined head-to-head chart:
[`agent_charts_v1_v2_tokens.png`](../../../raw-results/flyte-agent-benchmark/agent_charts_v1_v2_tokens.png).

**Group B is the capability gap, not an efficiency one.** v1 recorded
`infeasible=true` on **all 6/6** trials (`oom_retry`, `circuit_breaker`,
`agent_loop`) — every subagent independently concluded from the v1 cheatsheet
alone that catching a live task failure as control flow, racing concurrent
task promises with cancellation, and in-process checkpointed steps are not
expressible in Flyte v1, and each stopped in ~2 tool calls / ~31k tokens
rather than fake a workaround. v2 **solved all 6/6** — `@flyte.trace` for
per-step checkpointing (`agent_loop`), native `try/except` around a task call
plus `.override()` for the memory-tier escalation (`oom_retry`), and
`asyncio.wait(..., FIRST_COMPLETED)` + cancellation for the live race
(`circuit_breaker`) — at 52,819 tokens / 2.0 iterations mean, comparable in
cost to v2's group-A/C trials.

## What the failed iterations actually were

**v1** — framework-mechanics errors dominate (92–100% of logged errors),
clustering into three repeated root causes rediscovered independently by
nearly every trial:

1. `uv` resolves Python 3.13 by default, which older `flytekit`'s
   `PythonVersion` enum doesn't recognize (`ValueError: (3, 13) is not a
   valid PythonVersion`) — fixed by pinning `requires-python = ">=3.12,<3.13"`.
2. `remote.execute(wf, ...)` — the cheatsheet's own basic pattern — doesn't
   fast-package local source outside interactive/Jupyter mode, so the remote
   pod fails with `ModuleNotFoundError: No module named 'solution'`. Fixed
   inconsistently across trials via `interactive_mode_enabled=True`,
   `remote.register_script(...)`, or `remote.fast_register_workflow(...)` —
   three different subagents found three different fixes for the same gap.
3. `remote.execute()` with no explicit `version=` resolves to a stale
   already-registered entity, since every trial's script names its workflow
   `wf` in a module `solution` — an unversioned call can fetch a *different*
   trial's launch plan with a mismatched interface.

**v2** — far fewer failures overall (10/10 and 8/8 first-or-second-try in
groups A/C), and the ones that occurred were mostly one-off SDK/doc mismatches
rather than a repeated systemic gap: a `flyte.errors.OOMError` two-positional-arg
signature not matching the cheatsheet's one-arg example (`oom_retry`), and — in
both `circuit_breaker` trials — putting the raced candidates on separate remote
`@env.task` pods, where ~5s of pod-scheduling overhead swamped the sub-second
delay differences the race depends on; fixed by keeping candidates as
in-process `asyncio` coroutines under one task. No Python-version or
code-packaging friction analogous to v1's top two failure modes appeared.

Only 2 of v1's 41 logged errors, and 2 of v2's 5, were genuine logic bugs —
the rest were friction between each cheatsheet's documented happy path and
what actually submitting a real trial script to a live cluster requires.

## Methodology caveats

**Cross-trial collisions (both arms).** All 24 trials per arm ran
**concurrently** as parallel subagents against the same shared
`flytesnacks/development` project. In v1, several trials (`etl_join/t1`,
`fit_eval/t1`, `hpo/t0`, `conditional/t0`, and others) explicitly hit and
diagnosed a stale launch plan registered by a *concurrently-running sibling
trial* as one of their failed iterations, since every trial's script shares
the workflow name `wf` / module name `solution`. This inflated v1's iteration
counts somewhat above a serial baseline; v2's SDK appears less sensitive to
this (no v2 trial reported it), which is itself part of the efficiency gap
this run measured, not a separate confound — but a cleaner re-run would use
per-trial unique project/domain or serialize execution to remove it entirely.

**Reference-solution leakage (v2, more prominent).** The fairness checklist
requires the held-out reference solutions under `v1/solutions/` and
`v2/solutions/` be kept out of a subagent's context. Several v2 trials'
self-reports explicitly describe consulting them anyway — `conditional/t1`
("matching the pattern used in the benchmark's held-out reference solutions"),
`hpo/t0` ("confirmed only by peeking at the dependency header of a held-out
reference solution"), and `batch_inference/t0` (same phrasing) — and one v1
trial (`train_classifier/t0`) read a *sibling trial's* passing `solution.py`
rather than a held-out reference. Nothing in `trial_prompt.md` technically
forbids reading arbitrary repo paths, so this wasn't a hard constraint the
harness enforced, only a norm the trial prompt stated ("Do not fetch other
docs"). This likely lowered both arms' apparent iteration/token counts to
some degree — plausibly more for v2, since it was self-reported explicitly
in three separate v2 trials versus one v1 trial — meaning the true
head-to-head gap in an isolated-filesystem re-run could be *larger* than
1.78× (v1 has further to fall back to without the peeking, v2 was already
closer to first-try-correct). A stricter re-run should run each trial in an
isolated worktree/sandbox with only the cheatsheet and `inputs.json`
present, no sibling or reference solutions reachable at all.

## Raw data

- `raw-results/flyte-agent-benchmark/v1/agent_results.jsonl`,
  `raw-results/flyte-agent-benchmark/v2/agent_results.jsonl` — one row per
  trial (arm, spec, group, difficulty, seed, tokens, iterations, success,
  infeasible, errors, model, timestamp).
- `raw-results/flyte-agent-benchmark/agent_results_v1_v2.jsonl` — both arms
  concatenated, what `score.py` was run against for the headline table above.
- `raw-results/flyte-agent-benchmark/{v1,v2}/runs/<spec>/t<seed>/` — each
  trial's `inputs.json`, `solution.py`, and `run.log` (OAuth callback URLs
  redacted in the v1 set, where two leaked into `run.log`).
- `raw-results/flyte-agent-benchmark/{v1,v2}/agent_charts_tokens.png`,
  `raw-results/flyte-agent-benchmark/agent_charts_v1_v2_tokens.png` — charts
  from `score.py`.
