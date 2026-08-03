---
name: flyte-benchmark
description: Reproduce the Flyte v1 vs v2 (OSS) vs Union scaling benchmarks — fan-out, long-chain, concurrency, and the swarm scale/OOM test. Use when someone wants to run, reproduce, or extend these orchestration benchmarks and collect wall-clock, peak memory, and OOM results. Invoke with /flyte-benchmark
---

# Flyte Benchmark

Reproduces the scaling benchmarks comparing **Flyte v1**, **Flyte v2 (OSS)**, and
**Union**. The benchmarks live in `scripts/` of
[flyteorg/flyte-benchmarks](https://github.com/flyteorg/flyte-benchmarks), so they can be run by
hand or driven from here:

```bash
git clone https://github.com/flyteorg/flyte-benchmarks && cd flyte-benchmarks
```

## What it measures

Four workload shapes. Leaves are **core-sleep** tasks that run with no task pod,
so you measure *orchestration* cost, not pod startup.

| shape | script | stresses |
|---|---|---|
| fanout | `fanout.py` | one run, N parallel leaves — wide breadth |
| long_chain | `long_chain.py` | N nodes in series — sequential depth |
| concurrency | `concurrency.py` | hold M leaves live for a window — steady-state load |
| swarm | `swarm.py` | K independent fan-out runs at once — the scale / OOM test |

Each shape exists twice: `scripts/v2/` (Flyte v2 SDK) and `scripts/v1/`
(flytekit + flytepropeller), taking **identical flags** and printing the same
`RESULT_JSON:` line. `scripts/plot_results.py` is shared.

Metrics: end-to-end **wall-clock** (from the driver) and **peak memory + OOM** of
the orchestration pod (via `kubectl top`).

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/). Every script carries its dependencies in a
  PEP 723 header, so `uv run` installs them (and Python 3.12) on first use —
  no venv, and the two SDKs never share an environment.
- A Flyte config **per target cluster** (v1, v2-OSS, Union). Both SDKs discover
  it themselves: `FLYTECTL_CONFIG`, else `./config.yaml` / `./.flyte/config.yaml`
  (v2 only), else `~/.flyte/config.yaml`.
- Runs land in **flytesnacks / development** on every cluster, so results stay
  comparable; override with `FLYTE_BENCH_PROJECT` / `FLYTE_BENCH_DOMAIN`.
- `kubectl` access to the orchestration pod + `metrics-server` (for memory sampling).

## How to run

Run the **same commands against each cluster** so the comparison is
apples-to-apples — same task image and driver, no relaunching failures.

```bash
export FLYTECTL_CONFIG=~/.flyte/config.yaml       # <- the cluster under test

uv run scripts/v2/fanout.py      --n 1000
uv run scripts/v2/long_chain.py  --length 100
uv run scripts/v2/concurrency.py --m 5000 --hold 120
uv run scripts/v2/swarm.py       --k 25 --n 2000     # 50k actions
```

The v1 scripts take the same flags — swap `scripts/v2` for `scripts/v1` (with `FLYTECTL_CONFIG`
pointing at the v1 cluster's config):

```bash
uv run scripts/v1/fanout.py --n 1000
```

Each prints a `RESULT_JSON:{...}` line; append them to one file (`| tee -a
results.jsonl`) to chart later, and loop in the shell to sweep:

```bash
for l in 100 300 500; do uv run scripts/v2/long_chain.py --length $l | tee -a results.jsonl; done
```

Notes that keep v1 comparable: leaves are core-sleep there too (via a prebuilt
public image; `FLYTE_BENCH_V1_REGISTRY` builds your own), and every execution is
launched with `--max-parallelism 1000` to match the v2 SDK default —
flytepropeller's ~25 would throttle wide fan-outs for a reason unrelated to how
it orchestrates (`BENCH_MAX_PARALLELISM` to change it).

Memory + OOM: watch the orchestration pod while a workload runs. A restart
count that goes up mid-run means it was OOM-killed (exit 137) — that locates the
ceiling, so record it as a result rather than retrying.

```bash
kubectl -n flyte top pod -l app.kubernetes.io/name=flyte-binary --containers   # v2 / OSS
kubectl -n flyte top pod -l app.kubernetes.io/name=flytepropeller --containers # v1
```

## Recommended sweeps (match `reference_results.md`)

- **fanout**: `--n` 1000 → 6000 (v1 OOMs a *held* fan-out ~6k; v2 stays flat)
- **long_chain**: `--length` 100 → 500
- **concurrency**: `--m` 1000 → 40000, with `--hold 120`
- **swarm**: `--k` 2 → 100 with `--n 2000` (where OSS OOMs at 200k and Union does not)

## Collect + compare

```bash
uv run scripts/plot_results.py results.jsonl --out charts
```

Prints a summary table and writes `charts_walltime.png` and `charts_memory.png`.
Compare against **`reference_results.md`** — the numbers we measured. Absolute
values depend on cluster size / DB / network, but the *shape* should reproduce:
v2 beats v1 on every workload (~2× on a fan-out, ~3.5–4.4× on a long chain,
~1.2–1.7× on held concurrency) and has no per-run OOM cliff; Union pulls further
ahead wherever actions run concurrently and clears the 200k swarm that OOMs a
single-pod OSS executor, whose memory tracks *cumulative* actions (~54 MiB/1,000)
while Union keeps action state in ScyllaDB.

## Fairness checklist

- Same task image and driver on every cluster; failed runs are never relaunched.
- core-sleep leaves (no pods) so node memory never masks the orchestrator's limit.
- Wipe CRDs / let pod memory settle between runs (state from a prior run inflates
  the informer cache and confounds the next measurement).
