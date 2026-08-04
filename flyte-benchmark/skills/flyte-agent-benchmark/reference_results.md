# Reference results

Numbers from a real run of the **v1 (flytekit) arm only** — every trial ran a
subagent end-to-end against the live cluster at `development.uniondemo.run`
(project `flytesnacks`, domain `development`), through the actual `oracle.py`
grader, no simulation. Raw output — every `solution.py`, `inputs.json`,
`run.log`, plus `agent_results.jsonl` and the chart — is checked into
[`raw-results/flyte-agent-benchmark/v1/`](../../../raw-results/flyte-agent-benchmark/v1/).

**Run date:** 2026-08-04. **Model:** claude-sonnet-5 (session default, no
override). **Trials:** 2 per spec (seeds 0, 1) × 12 specs = 24. **Turn
budget:** 8 run→fix iterations.

**No v2 arm has been run yet** — this is a one-sided v1 baseline, not the
head-to-head comparison the benchmark is ultimately for. `score.py` reports
`—` for every v2 column below until that arm is run; re-run `score.py` over
`raw-results/flyte-agent-benchmark/v1/agent_results.jsonl` plus a v2
`agent_results.jsonl` to get the actual tokens/iterations ratio.

## Headline (v1 side only)

| group | trials | success | infeasible | tokens→green (mean) | out tokens (mean) | iters→green (mean) | framework-error share |
|---|---|---|---|---|---|---|---|
| A — core mechanics | 10 | 100% | 0 | 71,414 | 667 | 5.0 | 92% (22/24 errors) |
| B — v2-only capability | 6 | 0% | **6/6** | — | — | — | — |
| C — applied ML | 8 | 100% | 0 | 75,661 | 911 | 3.5 | 100% (17/17 errors) |

Every group-A and group-C trial eventually reached `ORACLE:PASS` — v1 can
express all of them — but at real cost: ~71–76k tokens and 3.5–5 run→fix
iterations per trial on average, ranging from a single-try 43.6k-token pass
(`etl`, easy) up to 115.5k tokens / 5 iterations (`train_classifier`, hard).

**Group B (`oom_retry`, `circuit_breaker`, `agent_loop`) came back infeasible
in all 6/6 trials**, exactly as predicted: v1 has no primitive for catching a
live task failure as control flow and re-launching with different resources,
no first-completed/cancel semantics over concurrent task promises, and no
in-process checkpointed-step primitive — every subagent independently reached
the same conclusion reading only the v1 cheatsheet, without being told the
answer, and each stopped in 2 tool calls / ~31k tokens rather than attempting
a fake workaround.

## What the failed iterations actually were

Framework-mechanics errors dominate (92–100% of logged errors), and they
cluster into the same handful of root causes, rediscovered independently
by nearly every trial:

1. **`uv` resolves Python 3.13 by default**, which older `flytekit`'s
   `PythonVersion` enum / `ImageConfig.auto_default_image()` doesn't
   recognize (`ValueError: (3, 13) is not a valid PythonVersion`) — fixed by
   pinning `requires-python = ">=3.12,<3.13"` in the PEP 723 header.
2. **`remote.execute(wf, ...)` — the cheatsheet's own basic pattern — doesn't
   fast-package local source** outside interactive/Jupyter mode, so the
   remote pod fails with `ModuleNotFoundError: No module named 'solution'`.
   Fixed inconsistently across trials via `interactive_mode_enabled=True`,
   `remote.register_script(...)`, or `remote.fast_register_workflow(...)` —
   three different subagents found three different fixes for the same gap,
   and one (`dynamic_fanout`) discovered `interactive_mode_enabled=True`
   silently doesn't support `@dynamic` tasks at all.
3. **`remote.execute()` with no explicit `version=` resolves to a stale
   already-registered entity** — every trial's script is named
   `solution.py` / workflow `wf`, so an unversioned call can fetch a
   different trial's launch plan with a mismatched interface
   (`FlyteLaunchPlan doesn't have this input key: ...`).

Only 2 of 41 logged errors were genuine logic bugs (an int/float type
mismatch in `fit_eval/t1`, a self-inflicted `UnboundLocalError` in
`dynamic_fanout/t0`) — the rest were friction between the cheatsheet's
documented happy path and what a non-interactive script actually needs to
submit and run against a real cluster.

## Methodology caveat: cross-trial collisions

All 24 trials ran **concurrently** as parallel subagents against the same
shared `flytesnacks/development` project, and every trial's solution defines
a workflow named `wf` in a module named `solution` (matching the cheatsheet's
own examples). Several trials (`etl_join/t1`, `fit_eval/t1`, `hpo/t0`,
`conditional/t0`, and others) explicitly hit and diagnosed a **stale launch
plan registered by a concurrently-running sibling trial** as one of their
failed iterations — a confound specific to running the harness's trials in
parallel, not something a single isolated v1 user would hit as often. This
likely inflated v1's mean iteration/token counts somewhat above a serial
baseline, though it's arguably realistic multi-tenant-cluster friction too.
Running the next batch (v2 arm, or a v1 re-run) with per-trial unique
project/domain or serialized execution would remove this confound if a
cleaner number is wanted.

## Raw data

- `raw-results/flyte-agent-benchmark/v1/agent_results.jsonl` — one row per
  trial (arm, spec, group, difficulty, seed, tokens, iterations, success,
  infeasible, errors, model, timestamp).
- `raw-results/flyte-agent-benchmark/v1/runs/<spec>/t<seed>/` — each trial's
  `inputs.json`, `solution.py`, and `run.log` (OAuth callback URLs redacted).
- `raw-results/flyte-agent-benchmark/v1/agent_charts_tokens.png` — chart from
  `score.py` (v1-only; v2 bars are empty until that arm runs).
