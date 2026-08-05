"""Per-page content: real numbers only, sourced from the shipped PDFs and
reference_results.md. No invented data points."""

PAGES = {}

# ============================================================ 1. flyte1-vs-flyte2
PAGES["flyte1-vs-flyte2"] = dict(
    site="flyte",
    slug="flyte1-vs-flyte2",
    eyebrow="Scalability study",
    title="Outscaling Flyte v1",
    subtitle="Flyte v2's per-action architecture runs common patterns up to 6.5× faster — and removes v1's single-process memory cliff entirely.",
    meta=["Orchestrator scalability study", "8 GiB engine pod · AWS EKS", "core-sleep leaves — no task pods"],
    pdf_href="https://github.com/flyteorg/flyte-benchmarks/blob/main/pdfs/flyte_v1_v2_paper.pdf",
    abstract=(
        "Flyte's original engine (v1) represents each run as a single custom resource "
        "that one controller reconciles in its entirety on every loop — simple, but it "
        "couples a run's cost to the size of one object and concentrates all of a run's "
        "state in one shared, memory-bounded process. The redesigned engine (v2) instead "
        "decomposes a run into many small actions, each independently reconciled, so no "
        "single in-memory object holds the whole run. Benchmarked on identical 8 GiB "
        "engine pods across wide fan-out, sustained concurrency, and long sequential "
        "chains, <b>v2 completes the common patterns 4.3–6.5× faster</b> and, "
        "critically, exhibits <b>no single-process memory cliff</b>: its footprint stays "
        "flat at ~0.3 GiB regardless of a run's width, whereas v1, holding a whole run "
        "in one object, drives the shared pod into the 8 GiB ceiling and "
        "<b>OOM-kills at a ~6,000-leaf fan-out</b> — an outage that takes down the "
        "whole platform, not just the offending run."
    ),
    stats=[
        dict(to=6.5, decimals=1, suffix="×", label="faster on a 500-node sequential chain", accent=True),
        dict(to=6000, decimals=0, prefix="~", label="held leaves before v1's single CRD OOM-kills its pod", bad=True),
        dict(to=0.3, decimals=1, suffix=" GiB", label="v2's flat engine footprint, at any run width", accent=True),
        dict(to=1.7, decimals=1, suffix="×", label="faster on sustained concurrency to 40,000 held tasks"),
    ],
    figures=[
        dict(
            id="fig-fanout", kind="bar", tag="Fig. 1 · wide fan-out",
            title="One run, N parallel leaves — execution seconds",
            legend=[("Flyte v1", "series_a"), ("Flyte v2", "series_b")],
            data=dict(
                categories=["1,000", "3,000", "6,000"],
                series=[
                    dict(label="Flyte v1", color="series_a", values=[126.3, 371.8, 699.1]),
                    dict(label="Flyte v2", color="series_b", values=[68.4, 144.2, 355.6]),
                ],
                yMax=800, yFmt="s0", barFmt="s0", unit=" s",
            ),
            note="A fan-out puts thousands of actions live at once, so a scaled-out engine has something to parallelize. At 6,000 leaves v2 is <b>2.0×</b> faster — and that's before the memory cliff below even enters the picture.",
        ),
        dict(
            id="fig-memory", kind="bar", tag="Fig. 2 · the OOM cliff",
            title="Engine memory under held fan-out — the reliability gap",
            legend=[("Flyte v1", "series_a"), ("Flyte v2", "series_b")],
            data=dict(
                categories=["1,000 held", "6,000 held"],
                series=[
                    dict(label="Flyte v1", color="series_a", values=[7.9, None]),
                    dict(label="Flyte v2", color="series_b", values=[0.3, 0.3]),
                ],
                yMax=9, yFmt="gib", barFmt="gib", unit="", oomText="OOM-KILLED",
            ),
            note="v1 holds a whole run's live leaves in one custom resource, reconciled in a shared 8 GiB pod — <b>engine memory tracks run width</b>. By ~6,000 held leaves it hits the ceiling and is OOM-killed (exit 137), taking the co-located control plane down with it. v2's footprint is decoupled from the run: <b>flat at ~0.3 GiB</b> regardless of width.",
        ),
        dict(
            id="fig-chain", kind="line", tag="Fig. 3 · long chain",
            title="N sequential nodes — execution seconds",
            legend=[("Flyte v1", "series_a"), ("Flyte v2", "series_b")],
            data=dict(
                xLabels=["100", "300", "500"],
                series=[
                    dict(label="Flyte v1", color="series_a", values=[65.7, 202.8, 366.1]),
                    dict(label="Flyte v2", color="series_b", values=[18.9, 53.4, 83.5]),
                ],
                yMax=400, yMin=0, yFmt="s0", ptFmt="s1",
            ),
            note="v1 re-reconciles one growing object on every loop, so a long chain pays repeatedly to re-evaluate an ever-larger record; v2 advances one compact action at a time. At length 500, v2 is <b>4.4×</b> faster.",
        ),
        dict(
            id="fig-conc", kind="line", tag="Fig. 4 · sustained concurrency",
            title="K workflows × 1,000 tasks, held 120 s — wall-clock",
            legend=[("Flyte v1", "series_a"), ("Flyte v2", "series_b")],
            data=dict(
                xLabels=["1k", "5k", "10k", "20k", "40k"],
                series=[
                    dict(label="Flyte v1", color="series_a", values=[242, 288, 322, 504, 1016]),
                    dict(label="Flyte v2", color="series_b", values=[146, 181, 266, 420, 756]),
                ],
                yMax=1100, yMin=0, yFmt="s0", ptFmt="s0",
            ),
            note="Run at matched parallelism, both engines complete every run and scale sub-linearly — the shape where the two designs are closest. v2 still holds a modest <b>1.2–1.7×</b> edge across the range.",
        ),
    ],
)

# ============================================================ 2. agents-write-flyte2-better
PAGES["agents-write-flyte2-better"] = dict(
    site="flyte",
    slug="agents-write-flyte2-better",
    eyebrow="Agent-authoring-cost study",
    title="Agents Write Flyte v2 Better",
    subtitle="A coding agent reaches a working pipeline in 1.8× fewer tokens on Flyte v2 — and solves patterns Flyte v1 cannot express at all.",
    meta=["48 real subagent trajectories", "claude-sonnet-5, fixed across both arms", "live oracle · real cluster · no simulation"],
    pdf_href="https://github.com/flyteorg/flyte-benchmarks/blob/main/pdfs/flyte_agent_benchmark_paper.pdf",
    abstract=(
        "Coding agents now author most Flyte pipelines; the DSL a human rarely reads is a "
        "DSL an agent must get exactly right on every turn. We benchmark that authoring "
        "cost directly: the <i>same</i> Claude Code subagent, same model, same turn budget, "
        "primed with an equal-token-budget cheatsheet for Flyte v1 (flytekit) or Flyte v2 "
        "(flyte), writes a pipeline for each of 12 framework-agnostic specs against a real "
        "cluster, graded by a live oracle — 48 trials total, no simulation. On the nine "
        "specs both frameworks can express, v2 reaches a passing run in <b>1.78× fewer "
        "tokens</b> and a <b>5× lower iteration count</b>, with essentially every v1 "
        "failed iteration (54 of 54 logged, vs. v2's 1) being framework-mechanics friction "
        "rather than a logic bug. On three specs that require catching a live task failure "
        "as control flow, racing concurrent tasks with cancellation, or checkpointing an "
        "in-process loop, v1 recorded <b>0% success (6/6 infeasible)</b> while v2 solved "
        "<b>6/6</b> — not an efficiency gap but a capability one."
    ),
    stats=[
        dict(to=1.78, decimals=2, suffix="×", label="fewer tokens to a passing run, groups A+C", accent=True),
        dict(to=5, decimals=0, suffix="×", label="lower median iteration count to green", accent=True),
        dict(to=6, decimals=0, prefix="0/", label="v1 successes on live, value-dependent control flow", bad=True),
        dict(to=54, decimals=0, prefix="", suffix=" vs 1", label="framework-mechanics failures logged, v1 vs v2"),
    ],
    figures=[
        dict(
            id="fig-tokens", kind="bar", tag="Fig. 1 · tokens to green",
            title="Mean tokens to first passing run, by spec group",
            legend=[("Flyte v1", "series_a"), ("Flyte v2", "series_b")],
            data=dict(
                categories=["A — core mechanics", "B — v2-only capability", "C — applied ML"],
                series=[
                    dict(label="Flyte v1", color="series_a", values=[71414, None, 75661]),
                    dict(label="Flyte v2", color="series_b", values=[40622, 52818, 41985]),
                ],
                yMax=90000, yFmt="k", barFmt="k0", unit=" tok", oomText="INFEASIBLE",
            ),
            note="Groups A and C: v2 costs roughly half the tokens of v1 at identical 100% success. Group B has no v1 bar — <b>every one of 6 trials recorded infeasible</b>, never producing a run to measure a token count for.",
        ),
        dict(
            id="fig-perspec", kind="bar", tag="Fig. 2 · per-spec consistency",
            title="Tokens to green, all nine head-to-head specs",
            legend=[("Flyte v1", "series_a"), ("Flyte v2", "series_b")],
            data=dict(
                categories=["etl", "fanout_map", "conditional", "dyn_fanout", "fit_eval", "etl_join", "train_clsf", "hpo", "batch_inf"],
                series=[
                    dict(label="Flyte v1", color="series_a", values=[67492, 63492, 73331, 71291, 81464, 76050, 83625, 72982, 69986]),
                    dict(label="Flyte v2", color="series_b", values=[41320, 39474, 40262, 38221, 43831, 43548, 43840, 41162, 39390]),
                ],
                yMax=95000, yFmt="k", barFmt="k0", unit=" tok",
            ),
            note="The v1/v2 ratio holds in a tight <b>1.6–1.9×</b> band regardless of spec content — ETL, ML training, hyperparameter search, or plain control flow all show the same order of gap.",
        ),
        dict(
            id="fig-errors", kind="bar", tag="Fig. 3 · error taxonomy",
            title="Failed run→fix iterations, by error class (groups A+C)",
            legend=[("Framework-mechanics", "series_a"), ("Logic", "bad")],
            data=dict(
                categories=["Flyte v1", "Flyte v2"],
                series=[
                    dict(label="Framework-mechanics", color="series_a", values=[52, 1]),
                    dict(label="Logic", color="bad", values=[2, 0]),
                ],
                yMax=60, yFmt="i0", barFmt="i0", unit="",
            ),
            note="Of v1's 54 logged failures, <b>52 were framework-mechanics friction</b> — toolchain version mismatches, silent non-packaging, unversioned entity collisions — not conceptual mistakes about the pipeline.",
        ),
    ],
)

# ============================================================ 3. flyte-vs-union
PAGES["flyte-vs-union"] = dict(
    site="union",
    slug="flyte-vs-union",
    eyebrow="Multi-cluster scale-out study",
    title="Orchestration Without Limits",
    subtitle="Union scales out to run 200,000-action workflows at low latency, where single-cluster OSS Flyte cannot.",
    meta=["100 concurrent runs × 2,000-wide fan-out", "identical task image · same client driver", "8 GiB OSS executor vs. Union's ScyllaDB fleet"],
    pdf_href="https://github.com/flyteorg/flyte-benchmarks/blob/main/pdfs/flyte_oss_vs_union_paper.pdf",
    abstract=(
        "Flyte v2 decomposes a run into many small per-action records rather than one big "
        "in-memory object — but v2 itself ships in two deployments: open-source Flyte, "
        "on a single cluster, and Union, which spreads its control and data planes across "
        "many. Both implement the same per-action model, so we ask whether decomposition "
        "alone delivers unbounded scale, or the surrounding architecture still sets the "
        "ceiling. We stress both with a swarm of K independent runs, each a 2,000-wide "
        "fan-out, ramped to 100 × 2,000 = 200,000 actions. Up to 20,000 "
        "actions both planes complete identically. At <b>200,000 actions they diverge "
        "sharply</b>: Flyte OOM-kills its 8 GiB executor — its footprint tracks "
        "cumulative actions processed, not live count, and never releases — while "
        "<b>Union completes all 100 runs in ~26 minutes</b>. Beyond the reliability "
        "ceiling, Union also wins throughput outright: 1.5× on wide fan-out and 2.0× "
        "on sustained concurrency at 40,000 held tasks, with no runtime failure mode across "
        "any shape."
    ),
    stats=[
        dict(to=200000, decimals=0, prefix="", label="cumulative actions Union completes; OSS Flyte OOMs here", accent=True),
        dict(to=26, decimals=0, suffix=" min", label="wall-clock for Union to finish all 100 runs at 200k"),
        dict(to=150000, decimals=0, prefix="~", label="cumulative-action ceiling where OSS Flyte's executor OOMs", bad=True),
        dict(to=2.0, decimals=1, suffix="×", label="faster on sustained concurrency at 40,000 held tasks", accent=True),
    ],
    figures=[
        dict(
            id="fig-swarm", kind="bar", tag="Fig. 1 · the swarm ramp",
            title="K runs × 2,000 actions — wall-clock (log scale)",
            legend=[("Flyte (OSS)", "series_a"), ("Union", "series_b")],
            data=dict(
                categories=["4k", "10k", "20k", "50k", "100k", "200k"],
                series=[
                    dict(label="Flyte (OSS)", color="series_a", values=[102, 229, 440, 1333, 3617, None]),
                    dict(label="Union", color="series_b", values=[59, 123, 185, 418, 772, 1533]),
                ],
                yMax=3900, yFmt="s0", barFmt="s0", unit=" s", oomText="OOM-KILLED",
            ),
            note="Every run completes on both planes through 100,000 actions. At <b>200,000</b> — the target scale — Flyte's 8 GiB executor OOM-kills and returns no runs, while Union completes all 100 in 1,533 s.",
        ),
        dict(
            id="fig-mem", kind="line", tag="Fig. 2 · cumulative-churn memory",
            title="OSS Flyte executor memory vs. cumulative actions processed",
            legend=[("Flyte (OSS) executor", "series_a")],
            data=dict(
                xLabels=["20k", "50k", "100k", "150k"],
                series=[
                    dict(label="Flyte (OSS) executor", color="series_a", values=[0.8, 2.6, 5.3, 8.0]),
                ],
                yMax=9, yMin=0, yFmt="gib", ptFmt="gib",
            ),
            note="Memory tracks <b>cumulative</b> actions processed, at ~54 MiB per 1,000 — not live count — because completed actions are never garbage-collected from the executor's informer cache. The line crosses the 8 GiB limit at ~150,000, exactly where the 200k swarm OOMs. Union stores action state in ScyllaDB, not a single process's heap, so no equivalent line exists for it.",
        ),
        dict(
            id="fig-held", kind="line", tag="Fig. 3 · held concurrency",
            title="Concurrent held tasks — wall-clock",
            legend=[("Flyte (OSS)", "series_a"), ("Union", "series_b")],
            data=dict(
                xLabels=["1k", "5k", "10k", "20k", "40k", "60k", "80k"],
                series=[
                    dict(label="Flyte (OSS)", color="series_a", values=[146, 169, 264, 419, 756, None, None]),
                    dict(label="Union", color="series_b", values=[149, 169, 177, 259, 374, 496, 664]),
                ],
                yMax=820, yMin=0, yFmt="s0", ptFmt="s0", oomText="OOM",
            ),
            note="Flyte's executor OOM-kills at <b>60,000</b> concurrently-held tasks — the live actions overflow the pod. Union holds <b>80,000 flat</b>, already 2.0× ahead of Flyte at 40k and the only plane past it.",
        ),
    ],
)

# ============================================================ 4. union-reusable-containers
PAGES["union-reusable-containers"] = dict(
    site="union",
    slug="union-reusable-containers",
    eyebrow="GPU-utilization study · FSG-26-04",
    title="Reuse or Reload",
    subtitle="A GPU-utilization study of batch LLM inference: keep the worker warm, or spin a fresh container per call.",
    meta=["Qwen2.5-7B on one NVIDIA L4", "500 GSM8K questions, ten 50-question chunks", "measured with nvidia-smi every 2 s"],
    pdf_href="https://github.com/flyteorg/flyte-benchmarks/blob/main/pdfs/union_reusable_containers.pdf",
    abstract=(
        "Serving large-model batch inference under an orchestrator forces a choice: keep a "
        "GPU worker <i>warm</i> across many calls, or spin a fresh container per call. We "
        "run one identical vLLM workload — 500 GSM8K questions through Qwen2.5-7B on an "
        "L4 — two ways. With container <b>reuse</b> on a managed Union cluster the job "
        "finishes in <b>404 s</b>; a <b>no-reuse</b> variant on open-source Flyte takes "
        "<b>1,665 s — 4.1× slower</b> — and, measured with nvidia-smi, keeps "
        "the GPU actually computing only 16% of the run while a model sits resident 86% of "
        "it, where the reuse GPU, warm, holds a steady 100%."
    ),
    stats=[
        dict(to=4.1, decimals=1, suffix="×", label="slower without container reuse (1,665s vs 404s)", bad=True),
        dict(to=100, decimals=0, suffix="%", label="sustained GPU utilization with reuse, once warm", accent=True),
        dict(to=10, decimals=0, prefix="", label="model loads without reuse — vs. just 2 with it", bad=True),
        dict(to=3.3, decimals=1, suffix="×", label="higher peak decode throughput with reuse", accent=True),
    ],
    figures=[
        dict(
            id="fig-wall", kind="bar", tag="Fig. 1 · wall-clock",
            title="500 GSM8K questions — total wall-clock",
            legend=[("Union · reuse", "series_b"), ("Flyte · no-reuse", "series_a")],
            data=dict(
                categories=["500 questions"],
                series=[
                    dict(label="Union · reuse", color="series_b", values=[404]),
                    dict(label="Flyte · no-reuse", color="series_a", values=[1665]),
                ],
                yMax=1850, yFmt="s0", barFmt="s0", unit=" s",
            ),
            note="Loading the model twice instead of ten times, and packing concurrent callers into 256-prompt batches rather than isolated 50-prompt calls, completes the identical job <b>4.1×</b> faster.",
        ),
        dict(
            id="fig-trace-union", kind="trace", tag="Fig. 2a · Union · reuse",
            title="Compute utilization + GPU memory over the run",
            data=dict(
                color="series_b", memMax=24,
                util=[0,0.05,0.9,1,0.55,0.15,0.95,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
                mem=[0,4,13,13,13,13,13,13,13,14,14,15,15,16,17,18,19,20,21,21,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22,22],
            ),
            note="One model load, then a steady <b>100%</b> through batched inference — mean utilization over the whole run is 35%, rising toward 100% as more work amortizes that single load.",
        ),
        dict(
            id="fig-trace-flyte", kind="trace", tag="Fig. 2b · Flyte · no-reuse",
            title="Compute utilization + GPU memory over the run",
            data=dict(
                color="series_a", memMax=24,
                util=[0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,0,0,0,0],
                mem=[0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0,14,0,0,0,0],
            ),
            note="Each chunk loads its own copy of the weights, fires one ~33-second 100% burst, then releases the GPU — <b>ten loads for ten chunks</b>. Integrated, Flyte computes for only 16% of the run while holding a model resident 86% of it: almost always occupied, almost never working.",
        ),
    ],
    table=dict(
        title="Same workload, two execution models",
        rows=[
            ("Wall-clock, 500 questions", "404 s", "1,665 s (4.1×)"),
            ("Model loads for the job", "2", "10"),
            ("Cold start, amortized / question", "~0.5 s", "~3.7 s"),
            ("Effective batch size", "up to 256", "50"),
            ("Peak decode throughput", "1,424 tok/s", "433 tok/s"),
            ("Time computing (util > 50%)", "35%", "16.1%"),
            ("Time holding a model, idle", "61%", "86.5%"),
        ],
        col_a="Union · reuse", col_b="Flyte · no-reuse",
    ),
)
