# benchmark

Reproducible **Flyte control-plane scaling benchmarks**, packaged as a Claude Code
plugin. Compares **Flyte v1**, **Flyte v2 (OSS)**, and **Union** on the same
workloads and collects wall-clock, peak memory, and OOM results.

This repo is a Claude Code **plugin marketplace** (`benchmark`) hosting one plugin
(`flyte-benchmark`). You can install it through Claude Code, or just clone the repo
and run the scripts directly — no Claude required.

---

## Install (Claude Code plugin)

```text
/plugin marketplace add flyteorg/benchmark
/plugin install flyte-benchmark@benchmark
```

Then invoke the skill:

```text
/flyte-benchmark:flyte-benchmark
```

Claude will walk you through running the workloads against whichever cluster your
Flyte config points at, collecting results, and comparing them to the reference
numbers.

To try it before it's on GitHub (local test):

```bash
/plugin marketplace add /path/to/this/repo
/plugin install flyte-benchmark@benchmark
```

---

## What it measures

Four workload shapes. Leaves are **core-sleep** tasks that run with no task pod,
so you measure *orchestration* cost, not pod startup.

| shape | what it stresses |
|---|---|
| `fanout` | one run, N parallel leaves — wide breadth |
| `long_chain` | N nodes in series — sequential depth |
| `concurrency` | hold M leaves live for a window — steady-state load |
| `swarm` | K independent fan-out runs at once — the scale / OOM test |

Metrics: end-to-end **wall-clock** (from the driver) and **peak memory + OOM** of
the orchestration pod (from `sample_mem.sh`).

---

## Results at a glance

Measured runs — identical 8 GiB orchestration pods for Flyte v1 and Flyte v2
(OSS), core-sleep leaves, same driver and retry budget everywhere. Full tables in
[`reference_results.md`](flyte-benchmark/skills/flyte-benchmark/reference_results.md);
regenerate the charts with `python charts/make_charts.py`.

**Steady-state concurrency** — the one shape run on all three planes. v2 is
1.2–1.7× faster than v1 across the range; both OSS planes are bounded by a single
pod's memory, and the OSS v2 executor is OOM-killed at ~60k held tasks. Union runs
the same v2 plane scaled out and keeps going to 80k.

![Concurrency runtime — Flyte v1 vs Flyte v2 (OSS) vs Union](charts/concurrency.png)

**Single-run shapes** — v1 keeps the whole run in one workflow CRD, so a single
reconcile loop churns it on every tick and its footprint grows with the run. v2
splits the run into per-action CRDs: ~6× faster on a wide fan-out and flat memory
down a long chain.

![Fan-out runtime and long-chain memory — v1 vs v2](charts/single_workflow.png)

**Swarm scale test** — K independent runs × 2,000 leaves. OSS executor memory
tracks *cumulative* actions (~54 MiB per 1,000), so an 8 GiB pod dies around 150k;
the 200k run never finished. Union holds action state in a distributed store and
completes all 100 runs.

![Swarm scale test — OSS v2 vs Union](charts/swarm.png)

---

## Usage (run it yourself)

Everything lives in `flyte-benchmark/skills/flyte-benchmark/`. Clone and run:

```bash
git clone https://github.com/flyteorg/benchmark
cd benchmark/flyte-benchmark/skills/flyte-benchmark
```

The workloads are split by control plane — `scripts/v2/` (Flyte v2 SDK) and
`scripts/v1/` (flytekit) — with `sample_mem.sh` and `plot_results.py` shared
between them. Each side has its own `requirements.txt` and needs its **own venv**:
`flyte` and `flytekit` can't be installed together.

```bash
python -m venv .venv-v2 && source .venv-v2/bin/activate
pip install -r scripts/v2/requirements.txt       # flyte v2 SDK (+ matplotlib)
export FLYTE_BENCH_CONFIG=~/.flyte/config.yaml   # <- config for the cluster under test
```

Run the **same commands against each cluster** (swap `FLYTE_BENCH_CONFIG`) so the
comparison is apples-to-apples — same image, driver, and retry budget everywhere.

### Example 1 — a quick single shape

```bash
python scripts/v2/_runner.py fanout n_children=1000 sleep_seconds=0
# -> SUBMITTED fanout url=... name=...
# -> RESULT_JSON:{"workload":"fanout","wall_seconds":29.1,"phase":"...SUCCEEDED",...}
```

### Example 2 — the standard sweep (fan-out, long-chain, concurrency)

```bash
R=scripts/v2/_runner.py
for N in 1000 6000; do python $R fanout      n_children=$N sleep_seconds=0 | tee -a results.jsonl; done
for L in 100 500;   do python $R long_chain  length=$L     sleep_seconds=0 | tee -a results.jsonl; done
for M in 1000 40000;do python $R concurrency m=$M hold_seconds=120         | tee -a results.jsonl; done
```

### Example 3 — the same shapes on a Flyte v1 cluster

v1 speaks flytekit, not the v2 SDK, so it gets its own scripts and venv. The
workloads, sweeps and `RESULT_JSON:` output line up with the v2 side.

```bash
deactivate; python -m venv .venv-v1 && source .venv-v1/bin/activate
pip install -r scripts/v1/requirements.txt
$EDITOR scripts/v1/config.yaml            # point admin.endpoint at your flyteadmin

python scripts/v1/_runner.py fanout      --n_children 1000 --sleep_duration 0s
python scripts/v1/_runner.py long_chain  --length 100      --sleep_duration 0s
python scripts/v1/_runner.py concurrency --m 1000 --hold_seconds 120
python scripts/v1/_runner.py nested      --depth 20 --width 5 --sleep_duration 0s

# swarm: K workflows x m held leaves (the v1 counterpart of Example 4)
python scripts/v1/swarm.py --k 10 --m 1000 --hold_seconds 120
```

Leaves use the core-sleep plugin here too — no task pods — so both planes are
measured on orchestration cost alone. Every execution is launched with
`--max-parallelism 1000` to match the v2 SDK default; flytepropeller's ~25 would
throttle wide fan-outs for a reason unrelated to its control plane.

### Example 4 — the swarm scale / OOM test

```bash
# K runs x 2000 leaves = up to 200k actions. This is where a single-pod OSS v2
# executor OOMs and a horizontally-scaled plane (Union) does not.
for K in 2 5 10 25 50 100; do
  python scripts/v2/swarm.py --k $K --n_children 2000 --sleep_seconds 1 --timeout 1800 --max-retries 0 \
    | tee -a results.jsonl
done
```

### Example 5 — capture peak memory + OOM (second terminal, while a run executes)

```bash
# v2 / OSS single-binary pod:
NS=flyte SEL='app.kubernetes.io/name=flyte-binary' CONT=flyte scripts/sample_mem.sh 1800
# v1: sample flytepropeller instead
NS=flyte SEL='app.kubernetes.io/name=flytepropeller' CONT=flytepropeller scripts/sample_mem.sh 1800
# -> PEAK_MEM_MIB=2032 RESTARTS_DELTA=0     (RESTARTS_DELTA>0 => OOMKilled, exit 137)
```

### Example 6 — summarize + chart, then compare

```bash
python scripts/plot_results.py results.jsonl --out charts
#   prints a summary table
#   writes charts_walltime.png and charts_memory.png (if matplotlib installed)
```

Compare your numbers to
[`reference_results.md`](flyte-benchmark/skills/flyte-benchmark/reference_results.md).
Absolute values depend on cluster size / DB / network, but the **shape** should
reproduce: v2 is ~4.3–6.5× faster than v1 with no per-run OOM cliff, and the OSS
executor OOMs the 200k swarm that Union completes.

---

## Recommended sweeps

| shape | sweep |
|---|---|
| `fanout` | `n_children` 1000 → 6000 (v1 OOMs a *held* fan-out ~6k; v2 stays flat) |
| `long_chain` | `length` 100 → 500 |
| `concurrency` | `m` 1000 → 40000, `hold_seconds=120` |
| `swarm` | `K` 2 → 100 (× 2000 leaves = up to 200k actions) |

---

## Prerequisites

- Python 3.12 and the Flyte v2 SDK (`pip install -r scripts/v2/requirements.txt`)
- For the v1 side: a **separate** venv with `pip install -r scripts/v1/requirements.txt`
  (flytekit + the core-sleep plugin) — flytekit and the v2 SDK can't coexist
- A Flyte config **per target cluster** (v1, v2-OSS, Union), selected via
  `FLYTE_BENCH_CONFIG` (default `~/.flyte/config.yaml`; the v1 scripts default to
  `scripts/v1/config.yaml`)
- For memory sampling: `kubectl` access to the orchestration pod + `metrics-server`

## Fairness checklist

- Same task image, driver, and `--max-retries` on every cluster.
- core-sleep leaves (no pods) so node memory never masks the control-plane limit.
- Wipe CRDs / let pod memory settle between runs (leftover state inflates the
  informer cache and confounds the next measurement).

## Layout

```
benchmark/                                  <- marketplace repo
  .claude-plugin/marketplace.json           <- marketplace catalog
  charts/                                   <- README charts + make_charts.py
  flyte-benchmark/                          <- the plugin
    .claude-plugin/plugin.json
    skills/flyte-benchmark/
      SKILL.md                              <- skill instructions
      reference_results.md                  <- numbers to compare against
      scripts/
        sample_mem.sh, plot_results.py      <- shared by both planes
        v2/                                 <- workloads + driver, Flyte v2 SDK
        v1/                                 <- the same workloads on flytekit/v1
```

## License

Apache-2.0
