# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.7"]
# ///
"""Regenerate the README charts from the measured numbers.

    uv run charts/make_charts.py     # writes charts/*.png

Every value below is a measurement from the runs recorded in
`flyte-benchmark/skills/flyte-benchmark/reference_results.md` — core-sleep leaves
(no task pods), identical 8 GiB orchestration pods for Flyte v1 and Flyte v2
(OSS). Nothing here is extrapolated: a deployment that OOM-killed gets no bar at that
scale, marked "OOM" instead, because it never produced a completion time.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

plt.rcParams.update({"font.family": "serif", "font.size": 11})

# Brand palette: Flyte v1 = muted violet, Flyte v2 = brand violet, Union = gold.
# BAD stays a warning red — it flags OOM/failure, not a product, so it must read
# as distinct from any brand bar.
V1, V2, UN, BAD = "#cbb7ff", "#8C4FFF", "#e0a800", "#c44e52"


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
    """Mark a slot where a deployment died instead of finishing — no bar, no height."""
    ax.annotate(text, (xpos, 0), textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=8.5, color=BAD, fontweight="bold")


def concurrency():
    """The one shape measured on all three: K runs x 1,000 tasks held 120 s."""
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


def fanout():
    """Wide fan-out on all three, re-run 2026-07-27 (same driver, same day)."""
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    bars(ax, ["1k", "3k", "6k"],
         [("Flyte v1 (OSS)", [126.3, 371.8, 699.1], V1),
          ("Flyte v2 (OSS)", [68.4, 144.2, 355.6], V2),
          ("Union (v2)", [19.0, 39.0, 68.6], UN)], fmt="{:.0f} s")
    for i, (v1, un) in enumerate([(126.3, 19.0), (371.8, 39.0), (699.1, 68.6)]):
        ax.annotate(f"Union {v1 / un:.1f}× v1", (i, v1), textcoords="offset points",
                    xytext=(0, 18), ha="center", fontsize=8.5, color="#8a6d00",
                    fontweight="bold")

    ax.set_xlabel("Leaves in one run")
    ax.set_ylabel("Execution time (s)")
    ax.set_title("Wide fan-out — thousands of actions live at once", fontsize=12)
    ax.set_ylim(0, 830)
    ax.legend(loc="upper left", frameon=False, fontsize=10.5)
    fig.tight_layout()
    fig.savefig("charts/fanout.png", dpi=150)
    print("wrote charts/fanout.png")


def long_chain():
    """Long chain on all three, re-run 2026-07-27 (same driver, same day)."""
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    bars(ax, ["100", "300", "500"],
         [("Flyte v1 (OSS)", [65.7, 202.8, 366.1], V1),
          ("Flyte v2 (OSS)", [18.9, 53.4, 83.5], V2),
          ("Union (v2)", [19.0, 53.5, 83.7], UN)], fmt="{:.1f} s", label_size=8)

    ax.annotate("v2 and Union land within 0.2 s at every length: a chain runs one\n"
                "action at a time, so scaling the orchestrator out has nothing to work with.\n"
                "The v1 gap is per-transition latency, not parallelism.",
                xy=(-0.42, 385), fontsize=9, color="#555", va="top")

    ax.set_xlabel("Chain length (nodes)")
    ax.set_ylabel("Execution time (s)")
    ax.set_title("Long chain — one action at a time", fontsize=12)
    ax.set_ylim(0, 430)
    ax.legend(loc="upper right", frameon=False, fontsize=10.5)
    fig.tight_layout()
    fig.savefig("charts/long_chain.png", dpi=150)
    print("wrote charts/long_chain.png")


def swarm():
    """K independent runs x 2,000 leaves.

    Left: all three at the same scale, same day. Right: how far each OSS
    deployment gets before it dies — the June ramp, where v1 was never run (a v1 swarm
    took 326 s at 10k actions; the 200k point would run for hours).
    """
    fig, ax = plt.subplots(1, 2, figsize=(11.0, 4.4),
                           gridspec_kw={"width_ratios": [1, 1.5]})

    a = ax[0]                                       # same-day, all three
    bars(a, ["4k", "10k"],
         [("Flyte v1 (OSS)", [300.8, 325.6], V1),
          ("Flyte v2 (OSS)", [69.2, 168.8], V2),
          ("Union (v2)", [54.1, 71.3], UN)], fmt="{:.0f} s")
    a.set_title("Same day, all three", fontweight="bold")
    a.set_xlabel("Total actions in flight")
    a.set_ylabel("Execution time (s)")
    a.set_ylim(0, 400)
    a.legend(loc="upper left", frameon=False, fontsize=9.5)

    b = ax[1]                                       # the scale ceiling (June build)
    cats = ["4k", "10k", "20k", "50k", "100k", "200k"]
    x, _ = bars(b, cats, [("Flyte v2 (OSS, one 8 GiB pod)", [102, 229, 440, 1333, 3617, None], V2),
                          ("Union (v2, scaled out)", [59, 123, 185, 418, 772, 1533], UN)],
                label_size=8)
    oom_marker(b, x[5] - 0.2)
    b.annotate("OSS is OOM-killed at 200k — peak 8.1 GiB. Executor memory\n"
               "tracks CUMULATIVE actions (~54 MiB / 1,000), so it has no bar here.",
               xy=(x[5] - 0.25, 250), xytext=(x[0] - 0.35, 3150), fontsize=8.5,
               color=BAD, fontweight="bold", ha="left", va="top",
               arrowprops=dict(arrowstyle="->", color=BAD, lw=.8,
                               connectionstyle="arc3,rad=-0.25"))
    b.set_title("The scale ceiling (earlier build; v1 not run at this scale)",
                fontweight="bold")
    b.set_xlabel("Total actions in flight")
    b.set_ylabel("Wall-clock runtime (s)")
    b.set_ylim(0, 4100)
    b.legend(loc="upper left", frameon=False, fontsize=9.5)

    fig.suptitle("Swarm — K independent runs × 2,000 leaves", fontsize=12, y=1.03)
    fig.tight_layout()
    fig.savefig("charts/swarm.png", dpi=150, bbox_inches="tight")
    print("wrote charts/swarm.png")


if __name__ == "__main__":
    concurrency()
    fanout()
    long_chain()
    swarm()
