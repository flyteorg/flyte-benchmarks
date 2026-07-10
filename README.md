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

## Usage (run it yourself)

Everything lives in `flyte-benchmark/skills/flyte-benchmark/`. Clone and run:

```bash
git clone https://github.com/flyteorg/benchmark
cd benchmark/flyte-benchmark/skills/flyte-benchmark

pip install -r requirements.txt          # flyte SDK (+ matplotlib for charts)
cd scripts
export FLYTE_BENCH_CONFIG=~/.flyte/config.yaml   # <- config for the cluster under test
```

Run the **same commands against each cluster** (swap `FLYTE_BENCH_CONFIG`) so the
comparison is apples-to-apples — same image, driver, and retry budget everywhere.

### Example 1 — a quick single shape

```bash
python _runner.py fanout n_children=1000 sleep_seconds=0
# -> SUBMITTED fanout url=... name=...
# -> RESULT_JSON:{"workload":"fanout","wall_seconds":29.1,"phase":"...SUCCEEDED",...}
```

### Example 2 — the v1-vs-v2 sweep (fan-out, long-chain, concurrency)

```bash
for N in 1000 6000; do python _runner.py fanout     n_children=$N sleep_seconds=0 | tee -a ../results.jsonl; done
for L in 100 500;   do python _runner.py long_chain length=$L    sleep_seconds=0 | tee -a ../results.jsonl; done
for M in 1000 40000;do python _runner.py concurrency m=$M hold_seconds=120        | tee -a ../results.jsonl; done
```

### Example 3 — the swarm scale / OOM test

```bash
# K runs x 2000 leaves = up to 200k actions. This is where a single-pod OSS v2
# executor OOMs and a horizontally-scaled plane (Union) does not.
for K in 2 5 10 25 50 100; do
  python swarm.py --k $K --n_children 2000 --sleep_seconds 1 --timeout 1800 --max-retries 0 \
    | tee -a ../results.jsonl
done
```

### Example 4 — capture peak memory + OOM (second terminal, while a run executes)

```bash
# v1 / OSS single-binary pod:
NS=flyte SEL='app.kubernetes.io/name=flyte-binary' CONT=flyte ./sample_mem.sh 1800
# -> PEAK_MEM_MIB=2032 RESTARTS_DELTA=0     (RESTARTS_DELTA>0 => OOMKilled, exit 137)
```

### Example 5 — summarize + chart, then compare

```bash
python plot_results.py ../results.jsonl --out ../charts
#   prints a summary table
#   writes ../charts_walltime.png and ../charts_memory.png (if matplotlib installed)
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

- Python 3.12 and the Flyte v2 SDK (`pip install flyte`)
- A Flyte config **per target cluster** (v1, v2-OSS, Union), selected via
  `FLYTE_BENCH_CONFIG` (default `~/.flyte/config.yaml`)
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
  flyte-benchmark/                          <- the plugin
    .claude-plugin/plugin.json
    skills/flyte-benchmark/
      SKILL.md                              <- skill instructions
      reference_results.md                  <- numbers to compare against
      requirements.txt
      scripts/                              <- workloads + drivers + sampler + plotter
```

## License

Apache-2.0
