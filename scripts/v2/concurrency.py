# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["flyte>=2.0.0"]
# ///
"""Steady-state concurrency — hold M leaves live for a window.

Same fan-out shape as fanout.py, but every leaf sleeps for `--hold` seconds, so
M actions stay RUNNING at once and the orchestrator reconciles them
continuously. This is the shape that finds the memory ceiling.

    uv run concurrency.py --m 1000 --hold 120
    uv run concurrency.py --m 40000 --hold 120
"""

from _common import leaves, parser, run_bench, task_env

env = task_env("bench_concurrency")


@env.task
async def hold_leaves(m: int = 1000, hold: int = 120) -> int:
    print(f"hold m={m} hold={hold}", flush=True)
    await leaves(m, hold)
    return m


if __name__ == "__main__":
    ap = parser("steady-state concurrency: hold M leaves live")
    ap.add_argument("--m", type=int, default=1000, help="leaves held live")
    ap.add_argument("--hold", type=int, default=120, help="seconds to hold them")
    a = ap.parse_args()
    run_bench("concurrency", hold_leaves, {"m": a.m, "hold": a.hold},
              total_actions=a.m, timeout=a.timeout)
