# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.7", "numpy>=1.24"]
# ///
"""Aggregate + chart the agent-authoring benchmark.

Reads a results file (one JSON line per trial, from record.py). Prints the
head-to-head v1-vs-v2 summary and writes charts.

    uv run score.py agent_results.jsonl [--out agent_charts]

The headline is **tokens to first green run** (harness-measured), averaged over
successful group-A trials, v1 vs v2, with the ratio. We also report iterations
to green, success rate, the framework-vs-logic error split (where the ergonomic
gap shows up), and the group-B capability outcome (v1 infeasible vs v2 solved).

Metrics with `tokens == null` (manual mode without a token meter) are dropped
from the token averages but still counted for iterations / success / taxonomy.
"""
import json
import statistics as st
import sys


def load(path):
    rows = []
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        if "RECORDED:" in line:
            line = line.split("RECORDED:", 1)[1]
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(st.mean(xs), 1) if xs else None


def _median(xs):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 1) if xs else None


def summarize(rows, arm, groups=None):
    if isinstance(groups, str):
        groups = {groups}
    r = [x for x in rows if x["arm"] == arm and (groups is None or x["group"] in groups)]
    solved = [x for x in r if x["success"]]
    tok = [x["tokens"] for x in solved if x.get("tokens") is not None]
    out_tok = [x["output_tokens"] for x in solved if x.get("output_tokens") is not None]
    errs = [e for x in r for e in x.get("errors", [])]
    fw = sum(1 for e in errs if e.get("class") == "framework")
    lg = sum(1 for e in errs if e.get("class") == "logic")
    return {
        "trials": len(r),
        "success_rate": round(len(solved) / len(r), 2) if r else None,
        "infeasible": sum(1 for x in r if x.get("infeasible")),
        "tokens_to_green": _mean(tok),
        "output_tokens": _mean(out_tok),
        "iterations_to_green": _median([x["iterations"] for x in solved]),
        "err_framework": fw,
        "err_logic": lg,
        "err_framework_frac": round(fw / (fw + lg), 2) if (fw + lg) else None,
    }


def _fmt(v):
    return "—" if v is None else str(v)


GROUP_NAME = {"A": "core mechanics", "B": "v2 capability", "C": "applied ML"}


def print_table(rows):
    cols = ["arm/group", "trials", "success", "infeas", "tokens→green",
            "out_tokens", "iters→green", "fw_err", "logic_err", "fw_frac"]
    print("  ".join(f"{c:>12}" for c in cols))
    groups = sorted({x["group"] for x in rows})
    cells = {}
    for grp in groups:
        for arm in ("v1", "v2"):
            s = summarize(rows, arm, grp)
            cells[(arm, grp)] = s
            vals = [f"{arm}/{grp}", s["trials"], s["success_rate"], s["infeasible"],
                    s["tokens_to_green"], s["output_tokens"], s["iterations_to_green"],
                    s["err_framework"], s["err_logic"], s["err_framework_frac"]]
            print("  ".join(f"{_fmt(v):>12}" for v in vals))

    # Headline: head-to-head = every group except the v2-only "B".
    head_groups = {g for g in groups if g != "B"}
    h1, h2 = summarize(rows, "v1", head_groups), summarize(rows, "v2", head_groups)
    label = "+".join(sorted(head_groups)) or "—"
    print(f"\nHeadline (head-to-head groups {label}):")
    if h1["tokens_to_green"] and h2["tokens_to_green"]:
        ratio = h1["tokens_to_green"] / h2["tokens_to_green"]
        print(f"  tokens to first green run — v1 {h1['tokens_to_green']} vs "
              f"v2 {h2['tokens_to_green']}  ({ratio:.2f}x {'fewer on v2' if ratio>1 else 'fewer on v1'})")
    else:
        print("  tokens to green: not enough harness-measured token data "
              "(tokens==null); compare iterations / success instead")
    if h1["iterations_to_green"] and h2["iterations_to_green"]:
        print(f"  iterations to green — v1 {h1['iterations_to_green']} vs "
              f"v2 {h2['iterations_to_green']} (median)")
    print(f"  success rate — v1 {_fmt(h1['success_rate'])} vs v2 {_fmt(h2['success_rate'])}")
    print(f"  framework-error fraction — v1 {_fmt(h1['err_framework_frac'])} vs "
          f"v2 {_fmt(h2['err_framework_frac'])}  (share of failures that are "
          f"framework-mechanics, not logic)")

    if "B" in groups:
        b1, b2 = cells[("v1", "B")], cells[("v2", "B")]
        print("\nGroup B (v2 capability, v1 expected infeasible):")
        print(f"  v1 — success rate {_fmt(b1['success_rate'])}, "
              f"infeasible {b1['infeasible']}/{b1['trials']}")
        print(f"  v2 — success rate {_fmt(b2['success_rate'])} over {b2['trials']} trials")
    return cells


def chart(rows, cells, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib not installed — skipping charts)")
        return
    # Per-spec mean tokens-to-green, v1 vs v2 (head-to-head groups A + C).
    specs = sorted({x["spec"] for x in rows if x["group"] != "B"})
    def cell(arm, spec):
        t = [x["tokens"] for x in rows if x["arm"] == arm and x["spec"] == spec
             and x["success"] and x.get("tokens") is not None]
        return _mean(t)
    v1 = [cell("v1", s) or 0 for s in specs]
    v2 = [cell("v2", s) or 0 for s in specs]
    if specs and (any(v1) or any(v2)):
        import numpy as np
        x = np.arange(len(specs))
        fig, ax = plt.subplots(figsize=(8, 4.3))
        ax.bar(x - 0.2, v1, 0.4, label="v1 (flytekit)", color="#a787ff")
        ax.bar(x + 0.2, v2, 0.4, label="v2 (flyte)", color="#5a27db")
        ax.set_xticks(x); ax.set_xticklabels(specs, rotation=30, ha="right")
        ax.set_ylabel("tokens to first green run")
        ax.set_title("Agent authoring cost — v1 vs v2 (head-to-head)")
        ax.legend(); fig.tight_layout()
        fig.savefig(f"{out}_tokens.png", dpi=150)
        print(f"\nwrote {out}_tokens.png")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = "agent_charts"
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    if not args:
        print(__doc__); sys.exit(1)
    rows = load(args[0])
    if not rows:
        print("no parseable result rows"); sys.exit(1)
    cells = print_table(rows)
    chart(rows, cells, out)


if __name__ == "__main__":
    main()
