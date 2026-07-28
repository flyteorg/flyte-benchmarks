# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["flyte>=2.0.0"]
# ///
"""Long chain — N nodes in one run, in series.

Leaves are awaited one at a time, so node state accumulates over many
transitions. Runtime is length × per-transition latency: this is the shape where
a scaled-out control plane has nothing to parallelize.

    uv run long_chain.py --length 100
    uv run long_chain.py --length 500
"""

from datetime import timedelta

from _common import parser, run_bench, sleep_leaf, task_env

env = task_env("bench_long_chain")


@env.task
async def chain(length: int = 100, sleep: int = 0) -> int:
    print(f"chain length={length}", flush=True)
    for _ in range(length):
        await sleep_leaf(seconds=timedelta(seconds=sleep))   # awaited in series
    return length


if __name__ == "__main__":
    ap = parser("long chain: N nodes in series")
    ap.add_argument("--length", type=int, default=100, help="nodes in the chain")
    ap.add_argument("--sleep", type=int, default=0, help="seconds each node sleeps")
    a = ap.parse_args()
    run_bench("long_chain", chain, {"length": a.length, "sleep": a.sleep},
              total_actions=a.length, timeout=a.timeout)
