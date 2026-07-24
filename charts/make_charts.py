"""Regenerate the README charts from the measured numbers.

    python charts/make_charts.py     # writes charts/*.png

Every value below is a measurement from the runs recorded in
`flyte-benchmark/skills/flyte-benchmark/reference_results.md` — core-sleep leaves
(no task pods), identical 8 GiB orchestration pods for Flyte v1 and Flyte v2
(OSS). Nothing here is extrapolated: where a plane OOM-killed, the series stops
and the point is marked.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({"font.family": "serif", "font.size": 11})

V1, V2, UN, BAD = "#c44e52", "#2f7ed8", "#e0a800", "#c44e52"


def concurrency():
    """The one shape measured on all three planes: K runs x 1,000 tasks held 120 s."""
    x = [1, 5, 10, 20, 40]
    v1 = [242, 288, 322, 504, 1016]                    # Flyte v1 (flytepropeller)
    v2 = [146, 181, 266, 420, 756]                     # Flyte v2 OSS (single executor pod)
    un_x = [1, 5, 10, 20, 40, 60, 80]
    un = [149, 169, 177, 259, 374, 496, 664]           # Union (v2 plane, scaled out)

    fig, ax = plt.subplots(figsize=(8.6, 4.7))
    ax.plot(x, v1, "-o", color=V1, lw=2, ms=7, label="Flyte v1 (OSS)")
    ax.plot(x, v2, "-s", color=V2, lw=2, ms=7, label="Flyte v2 (OSS)")
    ax.plot(un_x, un, "-^", color=UN, lw=2, ms=7, markeredgecolor="black",
            markeredgewidth=.5, label="Union (v2)")

    for xk, a, b in zip(x, v1, v2):                    # v1/v2 speedup at each point
        ax.annotate(f"{a / b:.1f}×", (xk, (a + b) / 2), textcoords="offset points",
                    xytext=(7, -2), fontsize=9, color="#555", fontweight="bold")

    # OSS never finished 60k held — dashed rise to an X means "no completion time".
    ax.plot([40, 58], [756, 1060], ls=(0, (4, 3)), color=BAD, lw=1.5)
    ax.scatter([58], [1060], marker="X", s=150, color=BAD, zorder=6)
    ax.annotate("Flyte v2 OSS OOM-killed\nat ~60k held (8 GiB pod)\n— run never completed",
                xy=(59, 1040), xytext=(62, 880), fontsize=8.5, color=BAD, fontweight="bold",
                ha="left", arrowprops=dict(arrowstyle="->", color=BAD, lw=.8))
    ax.annotate("Union keeps going:\n80k held in ~11 min", xy=(80, 664), xytext=(64, 330),
                fontsize=8.5, color="#8a6d00", ha="center",
                arrowprops=dict(arrowstyle="->", color="#8a6d00", lw=.8))

    ax.set_xlabel("Concurrent held tasks (thousands)")
    ax.set_ylabel("Wall-clock runtime (s)")
    ax.set_title("Steady-state concurrency — 1,000 tasks/run, held 120 s", fontsize=12)
    ax.set_xlim(0, 84)
    ax.set_ylim(0, 1150)
    ax.set_xticks(un_x)
    ax.legend(loc="upper left", frameon=False, fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", ls=":", alpha=.4)
    fig.tight_layout()
    fig.savefig("charts/concurrency.png", dpi=150)
    print("wrote charts/concurrency.png")


def single_workflow():
    """v1 vs v2 on single-run shapes — where v1's one-CRD-per-run design shows up."""
    fig, ax = plt.subplots(1, 2, figsize=(9.2, 3.9))

    a = ax[0]                                          # fan-out runtime
    k = [1, 2, 3, 4, 5, 6]
    a.plot(k, [124, 213, 350, 444, 579, 717], "-o", color=V1, lw=2, label="Flyte v1")
    a.plot(k, [29, 40, 55, 84, 100, 115], "-s", color=V2, lw=2, label="Flyte v2")
    a.annotate("6.2× faster", (6, 115), textcoords="offset points", xytext=(-6, 16),
               ha="right", color=V2, fontsize=9.5, fontweight="bold")
    a.set_title("Wide fan-out — runtime", fontweight="bold")
    a.set_xlabel("Leaves in one run (thousands)")
    a.set_ylabel("Wall-clock (s)")
    a.set_xticks(k)
    a.set_xticklabels([f"{i}k" for i in k])
    a.set_ylim(0, 780)
    a.legend(frameon=False, loc="upper left")

    b = ax[1]                                          # long-chain memory
    n = [100, 300, 500]
    b.plot(n, [1272, 1410, 1589], "-o", color=V1, lw=2, label="Flyte v1")
    b.plot(n, [298, 317, 327], "-s", color=V2, lw=2, label="Flyte v2")
    for xx, yy, c, dy in [(500, 1589, V1, 9), (500, 327, V2, -16)]:
        b.annotate(f"{yy} MiB", (xx, yy), textcoords="offset points", xytext=(-4, dy),
                   ha="right", color=c, fontsize=9)
    b.set_title("Long chain — control-plane memory", fontweight="bold")
    b.set_xlabel("Chain length (nodes)")
    b.set_ylabel("Peak memory (MiB)")
    b.set_xticks(n)
    b.set_ylim(0, 1800)
    b.legend(frameon=False, loc="center left")

    for p in ax:
        p.spines[["top", "right"]].set_visible(False)
        p.grid(axis="y", ls=":", alpha=.4)
    fig.suptitle("Single-run shapes: v1 holds the whole run in one workflow CRD; "
                 "v2 splits it into per-action CRDs", fontsize=9.5, color="#555", y=1.02)
    fig.tight_layout()
    fig.savefig("charts/single_workflow.png", dpi=150, bbox_inches="tight")
    print("wrote charts/single_workflow.png")


def long_chain():
    """OSS v2 vs Union on a sequential chain (re-run 2026-07-24, same driver/day).

    Newer builds than the v1-vs-v2 rows in panel B of single_workflow() — don't
    read the two figures against each other.
    """
    n = [100, 300, 500]
    oss = [18.9, 53.4, 83.5]                           # execution seconds, submit excluded
    union = [19.0, 53.5, 83.7]

    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.plot(n, oss, "-s", color=V2, lw=2.5, ms=9, label="Flyte v2 (OSS)")
    ax.plot(n, union, "--^", color=UN, lw=2, ms=8, markeredgecolor="black",
            markeredgewidth=.5, label="Union (v2)")
    for x, y in zip(n, oss):
        ax.annotate(f"{y:.0f} s", (x, y), textcoords="offset points", xytext=(0, -17),
                    ha="center", fontsize=9, color="#444")

    ax.annotate("The two planes overlap. A chain runs one\n"
                "action at a time, so a scaled-out plane has\n"
                "nothing to parallelize: runtime = length ×\n"
                "per-transition latency (~0.17 s/node).",
                xy=(215, 8), fontsize=9, color="#555")

    ax.set_xlabel("Chain length (nodes)")
    ax.set_ylabel("Execution time (s)")
    ax.set_title("Long chain — where scale-out does NOT help", fontsize=12)
    ax.set_xticks(n)
    ax.set_xlim(60, 540)
    ax.set_ylim(0, 100)
    ax.legend(loc="upper left", frameon=False, fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", ls=":", alpha=.4)
    fig.tight_layout()
    fig.savefig("charts/long_chain.png", dpi=150)
    print("wrote charts/long_chain.png")


def swarm():
    """The scale test: K independent runs x 2,000 leaves, up to 200k actions."""
    oss_x = [4, 10, 20, 50, 100]                       # thousands of actions
    oss_y = [102, 229, 440, 1333, 3617]                # K=50 finished 48/50
    un_x = [4, 10, 20, 50, 100, 200]
    un_y = [59, 123, 185, 418, 772, 1533]

    fig, ax = plt.subplots(figsize=(8.6, 4.5))
    ax.plot(oss_x, oss_y, "-s", color=V2, lw=2, ms=7, label="Flyte v2 (OSS, one 8 GiB pod)")
    ax.plot(un_x, un_y, "-^", color=UN, lw=2, ms=7, markeredgecolor="black",
            markeredgewidth=.5, label="Union (v2, scaled out)")

    # OSS never finished 200k — dashed rise to an X means "no completion time".
    ax.plot([100, 195], [3617, 3980], ls=(0, (4, 3)), color=BAD, lw=1.5)
    ax.scatter([195], [3980], marker="X", s=170, color=BAD, zorder=6)
    ax.annotate("OSS OOM-killed at 200k — peak 8.1 GiB.\nExecutor memory tracks CUMULATIVE\nactions (~54 MiB / 1,000).",
                xy=(190, 3900), xytext=(96, 2750), fontsize=8.5, color=BAD,
                fontweight="bold", ha="left",
                arrowprops=dict(arrowstyle="->", color=BAD, lw=.8))
    ax.annotate("Union completes 200k\nin ~26 min (100/100 runs)", xy=(200, 1533),
                xytext=(140, 650), fontsize=9, color="#8a6d00", ha="center",
                arrowprops=dict(arrowstyle="->", color="#8a6d00", lw=.8))

    ax.set_xlabel("Total actions in flight (thousands)")
    ax.set_ylabel("Wall-clock runtime (s)")
    ax.set_title("Swarm scale test — K runs × 2,000 leaves", fontsize=12)
    ax.set_xticks(un_x)
    ax.set_xlim(0, 215)
    ax.set_ylim(0, 4100)
    ax.legend(loc="upper left", frameon=False, fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", ls=":", alpha=.4)
    fig.tight_layout()
    fig.savefig("charts/swarm.png", dpi=150)
    print("wrote charts/swarm.png")


if __name__ == "__main__":
    concurrency()
    single_workflow()
    long_chain()
    swarm()
