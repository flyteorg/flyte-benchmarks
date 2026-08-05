# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.7"]
# ///
"""Regenerate the agent-authoring-cost paper's charts from the measured numbers.

    uv run charts/make_agent_charts.py     # writes charts/agent_*.png

Every value below is computed directly from
`raw-results/flyte-agent-benchmark/agent_results_v1_v2.jsonl` — 48 real trials
(12 specs x 2 seeds x 2 arms), each a subagent trajectory graded by a live
oracle against the real cluster. Nothing here is extrapolated: a v1 group-B
spec that came back `infeasible=true` gets no bar, marked "INFEASIBLE"
instead, because no v1 trial ever produced a passing run to measure.
"""
import json
import statistics as st

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

plt.rcParams.update({"font.family": "serif", "font.size": 11})

# Brand palette: Flyte v1 = muted violet, Flyte v2 = brand violet, warning red
# stays a status signal, not a product, so it must read as distinct from both.
V1, V2, BAD = "#a787ff", "#5a27db", "#c44e52"

ROWS = [json.loads(l) for l in
        open("raw-results/flyte-agent-benchmark/agent_results_v1_v2.jsonl")]


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


def infeasible_marker(ax, xpos, text="INFEASIBLE"):
    """Mark a slot where every trial recorded infeasible=true — no bar, no height."""
    ax.annotate(text, (xpos, 0), textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=8, color=BAD, fontweight="bold", rotation=0)


def _succ(arm, group=None, spec=None, difficulty=None):
    return [r for r in ROWS
            if r["arm"] == arm and r["success"]
            and (group is None or r["group"] == group)
            and (spec is None or r["spec"] == spec)
            and (difficulty is None or r["difficulty"] == difficulty)]


def headline():
    """Tokens- and iterations-to-green by group, both arms. The money chart:
    v1/B has no bar (6/6 infeasible) where v2/B does."""
    groups = ["A — core\nmechanics", "B — v2-only\ncapability", "C — applied\nML"]
    v1_tok, v2_tok, v1_it, v2_it = [], [], [], []
    for g in ["A", "B", "C"]:
        s1, s2 = _succ("v1", g), _succ("v2", g)
        v1_tok.append(st.mean(r["tokens"] for r in s1) if s1 else None)
        v2_tok.append(st.mean(r["tokens"] for r in s2) if s2 else None)
        v1_it.append(st.mean(r["iterations"] for r in s1) if s1 else None)
        v2_it.append(st.mean(r["iterations"] for r in s2) if s2 else None)

    fig, ax = plt.subplots(1, 2, figsize=(11.0, 4.6))

    x, _ = bars(ax[0], groups, [("Flyte v1", v1_tok, V1), ("Flyte v2", v2_tok, V2)],
                fmt="{:,.0f}")
    infeasible_marker(ax[0], x[1] - 0.16)
    ax[0].set_ylabel("Mean tokens to first green run")
    ax[0].set_title("Tokens to green", fontweight="bold")
    ax[0].set_ylim(0, 90000)
    ax[0].legend(loc="lower center", bbox_to_anchor=(0.5, 1.06), ncol=2,
                 frameon=False, fontsize=10)

    x, _ = bars(ax[1], groups, [("Flyte v1", v1_it, V1), ("Flyte v2", v2_it, V2)],
                fmt="{:.1f}")
    infeasible_marker(ax[1], x[1] - 0.16)
    ax[1].set_ylabel("Mean run→fix iterations to green")
    ax[1].set_title("Iterations to green", fontweight="bold")
    ax[1].set_ylim(0, 6.8)
    ax[1].legend(loc="lower center", bbox_to_anchor=(0.5, 1.06), ncol=2,
                 frameon=False, fontsize=10)

    fig.suptitle("Agent authoring cost — Flyte v1 vs v2, by spec group", fontsize=12, y=1.03)
    fig.tight_layout()
    fig.savefig("charts/agent_headline.png", dpi=150, bbox_inches="tight")
    print("wrote charts/agent_headline.png")


def per_spec():
    """Every group-A/C spec, v1 vs v2 tokens to green — the ratio holds everywhere."""
    specs = sorted({r["spec"] for r in ROWS if r["group"] in ("A", "C")})
    labels = [s.replace("_", "\n") for s in specs]
    v1 = [st.mean(r["tokens"] for r in _succ("v1", spec=s)) for s in specs]
    v2 = [st.mean(r["tokens"] for r in _succ("v2", spec=s)) for s in specs]

    fig, ax = plt.subplots(figsize=(11.0, 4.8))
    bars(ax, labels, [("Flyte v1", v1, V1), ("Flyte v2", v2, V2)],
         fmt="{:,.0f}", label_size=7.5)
    for i, (a, b) in enumerate(zip(v1, v2)):
        ax.annotate(f"{a / b:.2f}×", (i, max(a, b)), textcoords="offset points",
                    xytext=(0, 16), ha="center", fontsize=8, color="#555", fontweight="bold")
    ax.set_ylabel("Mean tokens to first green run")
    ax.set_title("Tokens to green by spec — groups A + C (both arms expressible)",
                  fontsize=12)
    ax.set_ylim(0, 100000)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2,
              frameon=False, fontsize=10.5)
    fig.tight_layout()
    fig.savefig("charts/agent_per_spec.png", dpi=150)
    print("wrote charts/agent_per_spec.png")


def errors():
    """Error taxonomy across all logged failed iterations, groups A+C."""
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    cats = ["Flyte v1", "Flyte v2"]
    fw, logic, unk = [], [], []
    for arm in ["v1", "v2"]:
        errs = [e for r in ROWS if r["arm"] == arm and r["group"] in ("A", "C")
                for e in r["errors"]]
        fw.append(sum(1 for e in errs if e["class"] == "framework"))
        logic.append(sum(1 for e in errs if e["class"] == "logic"))
        unk.append(sum(1 for e in errs if e["class"] == "unknown"))

    x = np.arange(len(cats))
    width = 0.6
    bottom = np.zeros(len(cats))
    for label, vals, color in [("Framework-mechanics", fw, V1),
                                ("Unknown / transient", unk, "#c9bfe8"),
                                ("Logic", logic, BAD)]:
        vals = np.array(vals, dtype=float)
        b = ax.bar(x, vals, width, bottom=bottom, label=label, color=color,
                   edgecolor="white", linewidth=.6, zorder=3)
        for xi, (v, bot) in enumerate(zip(vals, bottom)):
            if v > 0:
                ax.annotate(f"{int(v)}", (xi, bot + v / 2), ha="center", va="center",
                            fontsize=9, color="white" if color != "#c9bfe8" else "#444",
                            fontweight="bold")
        bottom += vals

    for xi, tot in enumerate(bottom):
        ax.annotate(f"{int(tot)} total", (xi, tot), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=9.5, color="#333", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(cats)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", ls=":", alpha=.4, zorder=0)
    ax.set_ylabel("Failed run→fix iterations, by error class")
    ax.set_title("What the failed iterations were — groups A + C", fontsize=12)
    ax.set_ylim(0, 62)
    ax.legend(loc="upper right", frameon=False, fontsize=10)
    fig.tight_layout()
    fig.savefig("charts/agent_errors.png", dpi=150)
    print("wrote charts/agent_errors.png")


def difficulty():
    """Tokens to green vs spec difficulty, groups A+C — v1 climbs, v2 stays flat."""
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    cats = ["Easy", "Medium", "Hard"]
    v1 = [st.mean(r["tokens"] for r in _succ("v1", difficulty=d.lower())
                  if r["group"] in ("A", "C")) for d in cats]
    v2 = [st.mean(r["tokens"] for r in _succ("v2", difficulty=d.lower())
                  if r["group"] in ("A", "C")) for d in cats]
    x = np.arange(len(cats))
    ax.plot(x, v1, "o-", color=V1, lw=2.4, ms=8, label="Flyte v1", zorder=3)
    ax.plot(x, v2, "s-", color=V2, lw=2.4, ms=8, label="Flyte v2", zorder=3)
    for xi, (a, b) in enumerate(zip(v1, v2)):
        ax.annotate(f"{a:,.0f}", (xi, a), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=9, color=V1, fontweight="bold")
        ax.annotate(f"{b:,.0f}", (xi, b), textcoords="offset points", xytext=(0, -16),
                    ha="center", fontsize=9, color=V2, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(cats)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", ls=":", alpha=.4, zorder=0)
    ax.set_ylabel("Mean tokens to first green run")
    ax.set_title("Authoring cost vs. spec difficulty — groups A + C", fontsize=12)
    ax.set_ylim(30000, 90000)
    ax.legend(loc="upper left", frameon=False, fontsize=10.5)
    fig.tight_layout()
    fig.savefig("charts/agent_difficulty.png", dpi=150)
    print("wrote charts/agent_difficulty.png")


if __name__ == "__main__":
    headline()
    per_spec()
    errors()
    difficulty()
