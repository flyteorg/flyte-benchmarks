"""Workload 1 — wide fan-out. One run, N parallel core-sleep leaves.

The single most discriminating v1-vs-v2 test: v1 grows one workflow CRD until it
hits the etcd/offload limit and reconcile slows quadratically; v2 spreads the
work across per-task-action CRDs.

Sweep n_children: 1000 -> 5000 -> 10000 -> 50000.
"""

import asyncio
from datetime import timedelta

import flyte

from _common import image, sleep_env, sleep_leaf

fanout_env = flyte.TaskEnvironment(
    name="bench_fanout",
    image=image,
    resources=flyte.Resources(cpu=(1, 2), memory=("2Gi", "4Gi")),
    depends_on=[sleep_env],
)


@fanout_env.task
async def fanout(n_children: int = 5000, sleep_seconds: int = 0) -> int:
    print(f"fanout n_children={n_children} sleep_seconds={sleep_seconds}", flush=True)
    await asyncio.gather(*(sleep_leaf(seconds=timedelta(seconds=sleep_seconds)) for _ in range(n_children)))
    return n_children


if __name__ == "__main__":
    flyte.init_from_config()
    r = flyte.with_runcontext("remote").run(fanout, n_children=5000, sleep_seconds=0)
    print(r.url)
