"""Workload 2 — steady-state concurrency. Hold M runs simultaneously running.

Keeps M leaves *in-flight* for a sustained window so the control plane
reconciles them continuously. Watch control-plane CPU/mem, reconcile/queue
latency, and backing-store load.

Sweep M: 500 -> 5000 -> 20000.
"""

import asyncio
from datetime import timedelta

import flyte

from _common import image, sleep_env, sleep_leaf

env = flyte.TaskEnvironment(
    name="bench_concurrency",
    image=image,
    resources=flyte.Resources(cpu=(1, 2), memory=("2Gi", "4Gi")),
    depends_on=[sleep_env],
)


@env.task
async def hold(m: int = 5000, hold_seconds: int = 300) -> int:
    """Hold `m` leaves running for `hold_seconds` — steady-state, not a burst."""
    print(f"hold m={m} hold_seconds={hold_seconds}", flush=True)
    await asyncio.gather(*(sleep_leaf(seconds=timedelta(seconds=hold_seconds)) for _ in range(m)))
    return m


if __name__ == "__main__":
    flyte.init_from_config()
    r = flyte.with_runcontext("remote").run(hold, m=5000, hold_seconds=300)
    print(r.url)
