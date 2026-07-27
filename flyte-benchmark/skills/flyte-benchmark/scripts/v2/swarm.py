# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["flyte>=2.0.0"]
# ///
"""Swarm — K independent runs at once, each a fan-out of N leaves.

The scale / OOM test, and the realistic shape: platforms get loaded by many
pipelines firing together, not by one pathologically wide run. Ramp K until runs
fail, submits time out, or the control plane is OOM-killed.

    uv run swarm.py --k 10 --n 2000
    uv run swarm.py --k 100 --n 2000     # 200k actions
"""

from _common import leaves, parser, run_bench, task_env

env = task_env("bench_swarm")


@env.task
async def wide(n: int = 2000, sleep: int = 1) -> int:
    await leaves(n, sleep)
    return n


if __name__ == "__main__":
    ap = parser("swarm: K concurrent runs of an N-wide fan-out")
    ap.add_argument("--k", type=int, default=10, help="concurrent runs")
    ap.add_argument("--n", type=int, default=2000, help="leaves per run")
    ap.add_argument("--sleep", type=int, default=1, help="seconds each leaf sleeps")
    a = ap.parse_args()
    run_bench("swarm", wide, {"n": a.n, "sleep": a.sleep},
              total_actions=a.k * a.n, timeout=a.timeout, k=a.k)
