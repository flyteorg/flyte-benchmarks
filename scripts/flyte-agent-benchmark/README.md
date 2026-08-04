# flyte-agent-benchmark — harness

Measures how many tokens / iterations a coding agent needs to write a **working**
Flyte pipeline, **v1 (flytekit) vs v2 (flyte)**, under an equal in-context
documentation budget. Driven by the `flyte-agent-benchmark` skill — see
`flyte-benchmark/skills/flyte-agent-benchmark/SKILL.md` for the full protocol.
This README is the quickstart for the scripts.

## Layout

```
specs.py          12 framework-agnostic pipeline specs + oracles (groups A/B/C)
make_inputs.py    write a trial's randomized inputs.json (seeded; strips hidden keys)
oracle.py         grade a produced output; --classify an error (framework/logic)
record.py         append one trial row to agent_results.jsonl
score.py          aggregate + chart v1 vs v2
count_tokens.py   token proxy (balance cheatsheets; output-token metric)
trial_prompt.md   the identical scaffold handed to each subagent
configure_cluster.py   fill the v2 org + print the run commands
config/v1.config.yaml  v1 (flytekit) cluster connection
config/v2.config.yaml  v2 (flyte) cluster connection
v1/cheatsheet.md  equal-budget docs for the v1 arm
v2/cheatsheet.md  equal-budget docs for the v2 arm
v1/solutions/     held-out reference solutions (HARNESS VALIDATION ONLY)
v2/solutions/
```

## Run on the cluster (`https://development.uniondemo.run/`)

Both arms connect via the files in `config/` (endpoint
`dns:///development.uniondemo.run`). Fill the v2 org once:

```bash
uv run configure_cluster.py --org <your-union-org>     # writes config/*.config.yaml
flyte whoami                                            # trigger/verify PKCE login (cached)
```

A solution runs remotely when `FLYTE_AGENT_BENCH_CONFIG` points at the arm's
config (its presence flips local -> remote); env doesn't persist across shells,
so pass it inline:

```bash
# v2 arm
FLYTE_AGENT_BENCH_CONFIG=$PWD/config/v2.config.yaml uv run v2/solutions/etl.py
# v1 arm (also set FLYTECTL_CONFIG for pyflyte)
FLYTE_AGENT_BENCH_CONFIG=$PWD/config/v1.config.yaml FLYTECTL_CONFIG=$PWD/config/v1.config.yaml \
    uv run v1/solutions/etl.py
```

Unset (or don't pass) `FLYTE_AGENT_BENCH_CONFIG` to run the same solution locally.

## Validate the harness (no cluster, no SDK needed)

```bash
uv run specs.py                              # every oracle self-tests -> PASS
uv run make_inputs.py conditional --seed 0 --show
echo 'TRIAL_OUTPUT_JSON:{"result":149}' | uv run oracle.py conditional --seed 0
uv run count_tokens.py v1/cheatsheet.md v2/cheatsheet.md   # should be within ~5%
```

## Smoke-test a reference solution (needs the SDK; local, no cluster)

The `solutions/` are the correct answers, held out from the agent under test —
use them only to confirm the specs are solvable and the oracle grades them:

```bash
uv run make_inputs.py etl --seed 0 --out /tmp/etl/inputs.json
cd /tmp/etl && cp <repo>/scripts/flyte-agent-benchmark/v2/solutions/etl.py solution.py
uv run solution.py | tee run.log                 # prints TRIAL_OUTPUT_JSON:{...}
uv run <repo>/scripts/flyte-agent-benchmark/oracle.py etl --inputs inputs.json --produced run.log
```

## The contract every solution follows

Read `inputs.json` from the working directory, run the pipeline on those inputs,
print exactly one line `TRIAL_OUTPUT_JSON:{...}` with the keys named in the spec's
output contract. Inputs are seeded and randomized, so only a real pipeline passes.

## Run the benchmark

Follow the skill. In short: for each `arm × spec × trial`, generate `inputs.json`,
spawn a subagent with `trial_prompt.md` (its **only** doc is that arm's
cheatsheet), record its `subagent_tokens` + `TRIAL_REPORT_JSON` via `record.py`,
then `score.py agent_results.jsonl`.
