# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.7"]
# ///
"""Regenerate the README charts from the measured numbers.

    uv run charts/make_charts.py     # writes charts/*.png

Every value below is a measurement from the runs recorded in
`flyte-benchmark/skills/flyte-benchmark/reference_results.md` — core-sleep leaves
(no task pods), identical 8 GiB orchestration pods for Flyte v1 and Flyte v2
(OSS). Nothing here is extrapolated: a plane that OOM-killed gets no bar at that
scale, marked "OOM" instead, because it never produced a completion time.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

plt.rcParams.update({"font.family": "serif", "font.size": 11})

V1, V2, UN, BAD = "#c44e52", "#2f7ed8", "#e0a800", "#c44e52"


def bars(ax, cats, series, fmt="{:.0f}", label_size=8.5):
    """Grouped bars. `series` is [(label, values, color)]; a None value = no data."""
    x = np.arange(len(cats))
    width = 0.8 / len(series)
    offset = -0.4 + width / 2
    for label, values, color in series:
        xs = [x[i] + offset for i, v in enumerate(values) if v is not None]
        ys = [v for v in values if v is not None]
        ax.bar(xs, ys, width, label=label, color=color,
               edgecolor="white", linewidth=.6, zorder=3)
        for xi, y in zip(xs, ys):
            ax.annotate(fmt.format(y), (xi, y), textcoords="offset points",
                        xytext=(0, 3), ha="center", fontsize=label_size, color="#444")
        offset += width
    ax.set_xticks(x)
    ax.set_xticklabels(cats)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", ls=":", alpha=.4, zorder=0)
    return x, width


def oom_marker(ax, xpos, text="OOM"):
    """Mark a slot where a plane died instead of finishing — no bar, no height."""
    ax.annotate(text, (xpos, 0), textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=8.5, color=BAD, fontweight="bold")


def concurrency():
    """The one shape measured on all three planes: K runs x 1,000 tasks held 120 s."""
    cats = ["1k", "5k", "10k", "20k", "40k", "60k", "80k"]
    v1 = [242, 288, 322, 504, 1016, None, None]
    v2 = [146, 181, 266, 420, 756, None, None]     # OOM-killed at 60k
    un = [149, 169, 177, 259, 374, 496, 664]

    fig, ax = plt.subplots(figsize=(9.0, 4.7))
    x, width = bars(ax, cats, [("Flyte v1 (OSS)", v1, V1),
                               ("Flyte v2 (OSS)", v2, V2),
                               ("Union (v2)", un, UN)])

    oom_marker(ax, x[5])                            # v2's slot at 60k
    ax.annotate("Flyte v2 OSS is OOM-killed at ~60k held (8 GiB pod).\n"
                "The run never completed, so it has no bar here.",
                xy=(x[5] - 0.05, 90), xytext=(x[4] + 0.3, 1120), fontsize=8.5,
                color=BAD, fontweight="bold", ha="left", va="top",
                arrowprops=dict(arrowstyle="->", color=BAD, lw=.8,
                                connectionstyle="arc3,rad=-0.2"))

    ax.set_xlabel("Concurrent held tasks")
    ax.set_ylabel("Wall-clock runtime (s)")
    ax.set_title("Steady-state concurrency — 1,000 tasks/run, held 120 s", fontsize=12)
    ax.set_ylim(0, 1150)
    ax.legend(loc="upper left", frameon=False, fontsize=10.5)
    fig.tight_layout()
    fig.savefig("charts/concurrency.png", dpi=150)
    print("wrote charts/concurrency.png")


def single_workflow():
    """v1 vs v2 on single-run shapes — where v1's one-CRD-per-run design shows up."""
    fig, ax = plt.subplots(1, 2, figsize=(9.6, 4.0))

    a = ax[0]                                       # fan-out runtime
    bars(a, ["1k", "2k", "3k", "4k", "5k", "6k"],
         [("Flyte v1", [124, 213, 350, 444, 579, 717], V1),
          ("Flyte v2", [29, 40, 55, 84, 100, 115], V2)], label_size=7.5)
    a.set_title("Wide fan-out — runtime", fontweight="bold")
    a.set_xlabel("Leaves in one run")
    a.set_ylabel("Wall-clock (s)")
    a.set_ylim(0, 830)
    a.annotate("v2 is 4–6× faster\nacross the range", (-0.4, 540), fontsize=9,
               color=V2, fontweight="bold", ha="left", va="top")
    a.legend(frameon=False, loc="upper left")

    b = ax[1]                                       # long-chain memory
    bars(b, ["100", "300", "500"],
         [("Flyte v1", [1272, 1410, 1589], V1),
          ("Flyte v2", [298, 317, 327], V2)])
    b.set_title("Long chain — control-plane memory", fontweight="bold")
    b.set_xlabel("Chain length (nodes)")
    b.set_ylabel("Peak memory (MiB)")
    b.set_ylim(0, 1850)
    b.legend(frameon=False, loc="upper left")

    fig.suptitle("Single-run shapes: v1 holds the whole run in one workflow CRD; "
                 "v2 splits it into per-action CRDs", fontsize=9.5, color="#555", y=1.02)
    fig.tight_layout()
    fig.savefig("charts/single_workflow.png", dpi=150, bbox_inches="tight")
    print("wrote charts/single_workflow.png")


def long_chain():
    """OSS v2 vs Union on a sequential chain (re-run 2026-07-24, same driver/day).

    Newer builds than the v1-vs-v2 numbers in single_workflow() — don't read the
    two figures against each other.
    """
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    bars(ax, ["100", "300", "500"],
         [("Flyte v2 (OSS)", [18.9, 53.4, 83.5], V2),
          ("Union (v2)", [19.0, 53.5, 83.7], UN)], fmt="{:.1f} s")

    ax.annotate("The two planes are within 0.2 s at every length.\n"
                "A chain runs one action at a time, so a scaled-out\n"
                "plane has nothing to parallelize: runtime is just\n"
                "length × per-transition latency (~0.17 s/node).",
                xy=(-0.42, 62), fontsize=9, color="#555")

    ax.set_xlabel("Chain length (nodes)")
    ax.set_ylabel("Execution time (s)")
    ax.set_title("Long chain — where scale-out does NOT help", fontsize=12)
    ax.set_ylim(0, 100)
    ax.legend(loc="upper left", frameon=False, fontsize=10.5)
    fig.tight_layout()
    fig.savefig("charts/long_chain.png", dpi=150)
    print("wrote charts/long_chain.png")


def swarm():
    """The scale test: K independent runs x 2,000 leaves, up to 200k actions."""
    cats = ["4k", "10k", "20k", "50k", "100k", "200k"]
    oss = [102, 229, 440, 1333, 3617, None]         # OOM-killed at 200k
    un = [59, 123, 185, 418, 772, 1533]

    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    x, _ = bars(ax, cats, [("Flyte v2 (OSS, one 8 GiB pod)", oss, V2),
                           ("Union (v2, scaled out)", un, UN)])

    oom_marker(ax, x[5] - 0.2)
    ax.annotate("OSS is OOM-killed at 200k — peak 8.1 GiB. Executor memory\n"
                "tracks CUMULATIVE actions (~54 MiB / 1,000), so it has no bar here.",
                xy=(x[5] - 0.25, 250), xytext=(x[0] - 0.35, 3150), fontsize=8.5,
                color=BAD, fontweight="bold", ha="left", va="top",
                arrowprops=dict(arrowstyle="->", color=BAD, lw=.8,
                                connectionstyle="arc3,rad=-0.25"))

    ax.set_xlabel("Total actions in flight")
    ax.set_ylabel("Wall-clock runtime (s)")
    ax.set_title("Swarm scale test — K runs × 2,000 leaves", fontsize=12)
    ax.set_ylim(0, 4100)
    ax.legend(loc="upper left", frameon=False, fontsize=10.5)
    fig.tight_layout()
    fig.savefig("charts/swarm.png", dpi=150)
    print("wrote charts/swarm.png")


if __name__ == "__main__":
    concurrency()
    single_workflow()
    long_chain()
    swarm()
