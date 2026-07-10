"""Workload 3 — depth. Deep nested subworkflows.

Each level calls the next inside a parent task, so the run is a chain of nested
parent->child actions `depth` deep (each parent also fans out `width` leaves to
keep transitions flowing). Stresses CRD size growth + per-transition reconcile
cost — v1 accretes node state in one workflow CRD.

Sweep depth: 20 -> 50.
"""

import asyncio
from datetime import timedelta

import flyte

from _common import image, sleep_env, sleep_leaf

env = flyte.TaskEnvironment(
    name="bench_nested",
    image=image,
    resources=flyte.Resources(cpu=1, memory="1Gi"),
    depends_on=[sleep_env],
)


@env.task
async def level(depth: int, width: int = 5) -> int:
    """Run `width` leaves, then recurse one level deeper until depth == 0."""
    await asyncio.gather(*(sleep_leaf(seconds=timedelta(0)) for _ in range(width)))
    if depth <= 0:
        return 0
    return 1 + await level(depth=depth - 1, width=width)


if __name__ == "__main__":
    flyte.init_from_config()
    r = flyte.with_runcontext("remote").run(level, depth=20, width=5)
    print(r.url)
