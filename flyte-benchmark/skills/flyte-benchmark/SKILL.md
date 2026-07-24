---
name: flyte-benchmark
description: Reproduce the Flyte v1 vs v2 (OSS) vs Union control-plane scaling benchmarks — fan-out, long-chain, concurrency, and the swarm scale/OOM test. Use when someone wants to run, reproduce, or extend these orchestration benchmarks and collect wall-clock, peak memory, and OOM results. Invoke with /flyte-benchmark
---

# Flyte Benchmark

Reproduces the control-plane scaling benchmarks comparing **Flyte v1**, **Flyte v2
(OSS)**, and **Union**. Everything is self-contained in this skill directory —
zip it and share it, or run it directly.

## What it measures

Four workload shapes. Leaves are **core-sleep** tasks that run with no task pod,
so you measure *orchestration* cost, not pod startup.

| shape | script | stresses |
|---|---|---|
| fanout | `fanout.py` | one run, N parallel leaves — wide breadth |
| long_chain | `long_chain.py` | N nodes in series — sequential depth |
| concurrency | `concurrency.py` | hold M leaves live for a window — steady-state load |
| swarm | `swarm.py` | K independent fan-out runs at once — the scale / OOM test |

The scripts above live in `scripts/v2/` (Flyte v2 SDK). The same shapes exist for
**Flyte v1** in `scripts/v1/` (flytekit + flytepropeller), plus `nested.py` for
depth — same sweeps, same `RESULT_JSON:` line. `scripts/sample_mem.sh` and
`scripts/plot_results.py` are shared by both.

Metrics: end-to-end **wall-clock** (from the driver) and **peak memory + OOM** of
the orchestration pod (from `sample_mem.sh`).

## Prerequisites

- Python 3.12 + the Flyte v2 SDK: `pip install -r scripts/v2/requirements.txt`
- For the v1 cluster: a **separate** venv with `pip install -r scripts/v1/requirements.txt`
  (flytekit + the core-sleep plugin). flytekit and the v2 SDK cannot share an env.
- A Flyte config **per target cluster** (v1, v2-OSS, Union). Point at one with
  `FLYTE_BENCH_CONFIG=/path/to/config.yaml` (default `~/.flyte/config.yaml`; the
  v1 scripts default to `scripts/v1/config.yaml`).
- `kubectl` access to the orchestration pod + `metrics-server` (for memory sampling).

## How to run

Run the **same commands against each cluster** so the comparison is apples-to-apples
(same task image, driver, and retry budget — that fairness is the whole point).

All paths below are relative to this skill directory.

```bash
export FLYTE_BENCH_CONFIG=~/.flyte/config.yaml    # <- the cluster under test

# single-run shapes — each prints a `RESULT_JSON:{...}` line; append to results.jsonl
R=scripts/v2/_runner.py
python $R fanout      n_children=1000 sleep_seconds=0 | tee -a results.jsonl
python $R long_chain  length=100      sleep_seconds=0 | tee -a results.jsonl
python $R concurrency m=5000 hold_seconds=120         | tee -a results.jsonl

# swarm scale test — ramp K (x 2000 leaves = up to 200k actions)
for K in 2 5 10 25 50 100; do
  python scripts/v2/swarm.py --k $K --n_children 2000 --sleep_seconds 1 --timeout 1800 --max-retries 0 \
    | tee -a results.jsonl
done
```

On a **Flyte v1** cluster, use the flytekit scripts instead (own venv; flags are
`--flag value`, durations in flytekit form):

```bash
$EDITOR scripts/v1/config.yaml            # admin.endpoint -> your flyteadmin

python scripts/v1/_runner.py fanout      --n_children 1000 --sleep_duration 0s
python scripts/v1/_runner.py long_chain  --length 100      --sleep_duration 0s
python scripts/v1/_runner.py concurrency --m 1000 --hold_seconds 120
python scripts/v1/_runner.py nested      --depth 20 --width 5 --sleep_duration 0s
python scripts/v1/swarm.py --k 10 --m 1000 --hold_seconds 120   # K workflows x m held leaves
```

Every v1 execution is launched with `--max-parallelism 1000` to match the v2 SDK
default (`BENCH_MAX_PARALLELISM` to change it) — flytepropeller's default of ~25
would throttle wide fan-outs for a reason unrelated to its control plane. Leaves
are core-sleep here too, via a prebuilt public image; set `FLYTE_BENCH_V1_REGISTRY`
to build your own instead.

Memory + OOM (run in a second terminal *while a workload executes*):

```bash
# v2 / OSS single-binary pod:
NS=flyte SEL='app.kubernetes.io/name=flyte-binary' CONT=flyte scripts/sample_mem.sh 1800
# v1: sample flytepropeller
NS=flyte SEL='app.kubernetes.io/name=flytepropeller' CONT=flytepropeller scripts/sample_mem.sh 1800
# prints  PEAK_MEM_MIB=<n> RESTARTS_DELTA=<n>   (RESTARTS_DELTA>0 => OOMKilled, exit 137)
```

## Recommended sweeps (match the papers)

- **fanout**: `n_children` 1000 → 6000 (v1 OOMs a *held* fan-out ~6k; v2 stays flat)
- **long_chain**: `length` 100 → 500
- **concurrency**: `m` 1000 → 40000, `hold_seconds=120`
- **swarm**: `K` 2 → 100 (this is where OSS OOMs at 200k and Union does not)

## Collect + compare

```bash
python scripts/plot_results.py results.jsonl --out charts
```

Prints a summary table and (if matplotlib is installed) writes `charts_walltime.png`
and `charts_memory.png`. Compare against **`reference_results.md`** — the numbers
we measured. The absolute values depend on cluster size / DB / network, but the
*shape* should reproduce: v2 is ~4.3–6.5x faster than v1 and has no per-run OOM
cliff; and the OSS executor OOMs the 200k swarm that Union completes, because OSS
memory tracks *cumulative* actions (~54 MiB/1,000) while Union leases only the live
set from ScyllaDB.

## Fairness checklist

- Same task image, same driver, same `--max-retries` on every cluster.
- core-sleep leaves (no pods) so node memory never masks the control-plane limit.
- Wipe CRDs / let pod memory settle between runs (state from a prior run inflates
  the informer cache and confounds the next measurement).
