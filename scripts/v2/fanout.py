# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["flyte>=2.0.0"]
# ///
"""Wide fan-out — one run, N parallel core-sleep leaves.

The most discriminating shape between the two versions: v1 grows one workflow CRD
until it hits the etcd/offload limit and reconcile slows down; v2 spreads the
same work over per-action CRDs.

    uv run fanout.py --n 1000
    uv run fanout.py --n 6000
"""

from _common import leaves, parser, run_bench, task_env

env = task_env("bench_fanout")


@env.task
async def fanout(n: int = 1000, sleep: int = 0) -> int:
    print(f"fanout n={n} sleep={sleep}", flush=True)
    await leaves(n, sleep)
    return n


if __name__ == "__main__":
    ap = parser("wide fan-out: one run, N parallel leaves")
    ap.add_argument("--n", type=int, default=1000, help="leaves in the run")
    ap.add_argument("--sleep", type=int, default=0, help="seconds each leaf sleeps")
    a = ap.parse_args()
    run_bench("fanout", fanout, {"n": a.n, "sleep": a.sleep},
              total_actions=a.n, timeout=a.timeout)
