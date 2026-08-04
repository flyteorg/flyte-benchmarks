---
name: flyte-agent-benchmark
description: Measure a coding agent's token efficiency at writing WORKING Flyte pipelines — v1 (flytekit) vs v2 (flyte). Runs the same natural-language pipeline specs through both SDKs under an equal in-context documentation budget, grades each attempt with a live programmatic oracle, and reports tokens-to-green, iterations, success rate, and the framework-vs-logic error split. Use when someone wants to run, reproduce, or extend the agent-authoring-cost benchmark. Invoke with /flyte-agent-benchmark
---

# Flyte agent-authoring benchmark

Measures a claim from the v1→v2 migration story: *holding the agent, the model,
and the documentation budget constant, a coding agent reaches a correct, running
pipeline in fewer tokens and fewer run→fix iterations when the target is Flyte
**v2** (`flyte`) than when it is Flyte **v1** (`flytekit`).*

This is the authoring-cost companion to the scaling benchmark in
`flyte-benchmark/` — same house style, same "real execution, no simulation,
failures reported not retried" philosophy, but the thing under test is the
**agent writing the code**, not the cluster running it.

## How it works

The unit of measurement is **one trial = one agent trajectory**. For a given
pipeline spec and a given arm (v1 or v2), a subagent is handed:

- the **same** natural-language spec (framework-agnostic — it names a data
  transformation and an output contract, never a Flyte API),
- **only** that arm's cheatsheet as its documentation (the two cheatsheets are
  token-balanced — that is the "equal in-context docs" control),
- a live oracle it must satisfy: write `solution.py` → run it → grade → fix,
  until a real run produces the correct output.

Running the trial as a **subagent** is what makes the headline number rigorous:
the harness reads the subagent's reported `subagent_tokens` — the tokens it
actually spent reaching a green run — rather than any self-estimate. Identical
scaffolding across arms (`scripts/flyte-agent-benchmark/trial_prompt.md`) keeps
the two comparable; the only things that differ are the arm name and its
cheatsheet.

### Metrics

- **Tokens to first green run** — `subagent_tokens` for the trial. *The headline.*
  Averaged over successful trials, v1 vs v2, with the ratio.
- **Iterations to green** — run→fix cycles until the first `ORACLE:PASS`.
- **Success rate** at a fixed turn budget.
- **Error taxonomy** — fraction of failed iterations that are *framework-mechanics*
  errors (Promise misuse, `conditional`/`@dynamic` confusion, compile/registration
  failures, a forgotten `await`) vs genuine *logic* errors. This is where the
  ergonomic gap shows up most directly.
- **Output-token volume** — `count_tokens.py` over the final `solution.py`, a
  proxy for boilerplate.

## The task suite

Eight specs (`scripts/flyte-agent-benchmark/specs.py`), graded easy→hard, in two
groups:

| group | spec | difficulty | tests |
|---|---|---|---|
| **A** head-to-head | `etl` | easy | task→task, passing outputs |
| | `fanout_map` | easy | static fan-out / map |
| | `conditional` | medium | runtime branch (`conditional` DSL vs native `if`) |
| | `dynamic_fanout` | medium | data-dependent width (`@dynamic` vs native `for`) |
| | `fit_eval` | hard | multi-stage, multiple named outputs |
| **B** v2 capability | `oom_retry` | hard | catch OOM, re-run step with more memory |
| | `circuit_breaker` | hard | race live tasks, cancel losers, open on failures |
| | `agent_loop` | hard | durable checkpointed tool loop |

**Group A** is the token/iteration comparison — every spec is expressible in
both arms. **Group B** are the value-dependent, in-process control-flow patterns
v1 cannot express even with `@dynamic`; the v1 arm is expected to record
`infeasible`, which is itself the result (the capability gap, not a token count).

Each spec ships a deterministic oracle: inputs are randomized per trial (seeded),
and the correct output is computed in plain Python, so **only a real pipeline
passes** — a hardcoded answer fails across seeds.

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/). Every harness script and every `solution.py`
  carries a PEP 723 header, so `uv run` installs `flytekit` / `flyte` (and the
  right Python) on first use — the two SDKs never share an environment.
- **Grading mode:**
  - **`local` (default, cheap).** `solution.py` runs the pipeline in-process, no
    cluster: `python solution.py` for v1 (a `@workflow` called at top level
    executes locally and returns real values), `flyte` local run for v2. Local
    execution surfaces essentially all *framework-mechanics* errors — the ones
    the benchmark is about — so it is the right default for measuring authoring
    cost.
  - **`remote` (faithful oracle).** Point each arm at a real v1 / v2 cluster
    (same config discovery as the sibling skill: `FLYTECTL_CONFIG`, else
    `~/.flyte/config.yaml`) and have `solution.py` submit remotely. Use this for
    the headline report; note it in the results.
  - **Grade group B (`oom_retry` especially) on a cluster.** Local execution
    never enforces memory limits, and a child task's `OOMError` caught in a
    parent is re-wrapped as `flyte.errors.RuntimeUserError` locally — so a
    genuine OOM cannot be triggered in local mode and the escalation loop must
    catch both types to run there at all. The v2 reference solution does; treat
    the local group-B run as a smoke test and the cluster run as the real oracle.
- The model driving the agent is whatever the operator runs this session with —
  keep it **fixed across both arms** for a given comparison.

## Running it — automated (recommended)

You (the agent invoking this skill) are the **orchestrator**. Do not author the
pipelines yourself — spawn one subagent per trial so the token count is measured,
not estimated. Loop over `arms × specs × trials`.

Suggested defaults: `TRIALS=2` per (arm, spec), `TURN_BUDGET=8`. That is
`8 arms-specs... ` → 2 arms × 8 specs × 2 trials = **32 subagents**. Halve
`TRIALS` for a quick pass. Announce the count before starting — this spends real
tokens.

For each trial `(arm, spec, seed)`:

1. **Make the workspace + inputs** (seed = trial index):
   ```bash
   uv run scripts/flyte-agent-benchmark/make_inputs.py <spec> --seed <n> \
       --out runs/<arm>/<spec>/t<n>/inputs.json
   ```
2. **Spawn the subagent.** Build its prompt from
   `scripts/flyte-agent-benchmark/trial_prompt.md`, filling the slots:
   `{{ARM}}`=`v1`|`v2`, `{{CHEATSHEET_PATH}}`=`scripts/flyte-agent-benchmark/<arm>/cheatsheet.md`,
   `{{SPEC_PROMPT}}`=the spec's `prompt` (print it with
   `uv run scripts/flyte-agent-benchmark/make_inputs.py <spec> --seed <n> --show`
   for inputs; the prompt text lives in `specs.py`), `{{SPEC_ID}}`=`<spec>`,
   `{{WORKDIR}}`=`runs/<arm>/<spec>/t<n>`, `{{HARNESS_DIR}}`=`scripts/flyte-agent-benchmark`,
   `{{TURN_BUDGET}}`=`8`. Use a plain general-purpose subagent; **do not** raise
   its model/effort above the session default — fairness requires the same model
   on both arms.
3. **Record the result.** From the subagent's final `TRIAL_REPORT_JSON` line and
   its reported `subagent_tokens`:
   ```bash
   uv run scripts/flyte-agent-benchmark/record.py --arm <arm> --spec <spec> \
       --seed <n> --trial <n> --tokens <subagent_tokens> \
       --iterations <iterations> [--success|--fail] [--infeasible] \
       --output-tokens $(uv run scripts/flyte-agent-benchmark/count_tokens.py runs/<arm>/<spec>/t<n>/solution.py | awk '{print $1}') \
       --errors '<errors JSON from the report>' --model <model> \
       --out agent_results.jsonl
   ```
   For a group-B v1 trial the subagent should return `infeasible=true`; record it
   with `--fail --infeasible` and no `--tokens`.

Spawn trials in parallel where you can (independent subagents), but keep each
arm's model identical.

## Running it — manual (one trial, no subagent)

To sanity-check the loop yourself: `make_inputs.py` → read
`<arm>/cheatsheet.md` → write `runs/.../solution.py` → run it → `oracle.py`
→ fix → repeat, then `record.py` (leave `--tokens` off — there is no
per-trajectory meter in manual mode; iterations/success/taxonomy still count).

## Score + interpret

```bash
uv run scripts/flyte-agent-benchmark/score.py agent_results.jsonl --out agent_charts
```

Prints the v1-vs-v2 table and the headline (group-A tokens-to-green ratio,
iterations, success rate, framework-error fraction), the group-B capability
outcome, and writes `agent_charts_tokens.png`. The *direction* is the claim:
v2 reaches green in fewer tokens and fewer iterations, with a lower share of
framework-mechanics errors; v1 records the group-B specs as infeasible while v2
solves them.

## Fairness checklist

- **Equal docs budget.** Re-check the two cheatsheets are token-balanced:
  `uv run scripts/flyte-agent-benchmark/count_tokens.py scripts/flyte-agent-benchmark/{v1,v2}/cheatsheet.md`
  (keep within ~5%). The cheatsheet is the *only* documentation a subagent gets.
- **Same model, same scaffold, same turn budget** on both arms; randomize/interleave
  trial order; run `K` trials per spec per arm to average out stochasticity.
- **Never relaunch a failed trial** to get a better number — record it as-is. A
  timed-out or infeasible trial is a result.
- **Confounder — training data.** v2 is newer, so models have seen less of it.
  The equal-docs control is the mitigation; report the confounder explicitly. The
  ergonomic advantage is structural (v2 is ordinary async Python with native
  control flow), so where v2 wins *despite* less training data, the advantage is
  real, not an artifact.
- **Hold-out.** The reference solutions under `<arm>/solutions/` are for
  validating the harness only — never place them, or their contents, in a
  subagent's context.

## Files

- `specs.py` — the 8 specs + deterministic oracles (`uv run specs.py` self-tests).
- `make_inputs.py` — write a trial's randomized `inputs.json` (or `--show`).
- `oracle.py` — grade a produced output; `--classify` an error as framework/logic.
- `record.py` — append one trial row to `agent_results.jsonl`.
- `score.py` — aggregate + chart v1 vs v2.
- `count_tokens.py` — token proxy (cheatsheet balancing; output-token metric).
- `trial_prompt.md` — the identical subagent scaffold.
- `v1/cheatsheet.md`, `v2/cheatsheet.md` — the equal-budget arm docs.
- `v1/solutions/`, `v2/solutions/` — held-out reference solutions (harness
  validation; never shown to the agent under test).
