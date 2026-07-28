# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.7"]
# ///
"""Summarize + chart collected benchmark results.

Reads a results file where each line is a JSON object emitted by the benchmark
scripts. Strips any `RESULT_JSON:` prefix, so you can just append their stdout.

Usage:
  uv run scripts/plot_results.py results.jsonl [--out charts]

Prints a summary table and writes:
  <out>_walltime.png  (wall-clock vs scale, one line per workload)
  <out>_memory.png    (peak_mem_mib vs scale, if present)
"""
import json
import sys


def load(path):
    rows = []
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        if "RESULT_JSON:" in line:
            line = line.split("RESULT_JSON:", 1)[1]
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


def scale_of(r):
    """Best-effort scalar 'scale' for a row, per workload."""
    p = r.get("params", {})
    for k in ("total_actions", "n", "length", "m", "k"):
        if k in r and isinstance(r[k], (int, float)):
            return r[k]
        if k in p and isinstance(p[k], (int, float)):
            return p[k]
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = "charts"
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    if not args:
        print(__doc__)
        sys.exit(1)
    rows = load(args[0])
    if not rows:
        print("no parseable result rows found")
        sys.exit(1)

    # summary table
    cols = ["workload", "scale", "wall_seconds", "peak_mem_mib", "succeeded", "failed", "oomed", "timed_out"]
    print("  ".join(f"{c:>13}" for c in cols))
    series = {}   # workload -> [(scale, wall, mem)]
    for r in sorted(rows, key=lambda r: (r.get("workload", ""), scale_of(r) or 0)):
        wl = r.get("workload", "?")
        sc = scale_of(r)
        vals = [wl, sc, r.get("wall_seconds"), r.get("peak_mem_mib"),
                r.get("succeeded", r.get("final_succeeded")), r.get("failed"),
                r.get("oomed"), r.get("timed_out")]
        print("  ".join(f"{str(v):>13}" for v in vals))
        series.setdefault(wl, []).append((sc, r.get("wall_seconds"), r.get("peak_mem_mib")))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib not installed — skipping charts; pip install matplotlib)")
        return

    # wall-clock vs scale
    fig, ax = plt.subplots(figsize=(7, 4.3))
    for wl, pts in series.items():
        pts = sorted((s, w) for s, w, _ in pts if s is not None and w is not None)
        if pts:
            xs, ys = zip(*pts)
            ax.plot(xs, ys, "-o", label=wl)
    ax.set_xlabel("scale (actions / leaves / length / held)")
    ax.set_ylabel("wall-clock (s)")
    ax.set_title("Benchmark wall-clock vs scale")
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{out}_walltime.png", dpi=150)
    print(f"\nwrote {out}_walltime.png")

    # memory vs scale (only if any mem present)
    mem_pts = {wl: sorted((s, m) for s, _, m in pts if s is not None and m is not None)
               for wl, pts in series.items()}
    if any(mem_pts.values()):
        fig, ax = plt.subplots(figsize=(7, 4.3))
        for wl, pts in mem_pts.items():
            if pts:
                xs, ys = zip(*pts)
                ax.plot(xs, ys, "-o", label=wl)
        ax.axhline(8192, ls="--", color="#c44e52", label="8 GiB limit")
        ax.set_xlabel("scale")
        ax.set_ylabel("peak memory (MiB)")
        ax.set_title("Peak orchestration-pod memory vs scale")
        ax.legend()
        fig.tight_layout()
        fig.savefig(f"{out}_memory.png", dpi=150)
        print(f"wrote {out}_memory.png")


if __name__ == "__main__":
    main()
