"""Workload 4 — long sequential DAG. Hundreds of nodes in one run, in series.

Sequential (not parallel) so node state accumulates over many transitions in a
single execution. Tests CRD accretion + offload behavior over time — v1's
workflow CRD grows with every completed node.

Sweep length: 100 -> 500.
"""

from datetime import timedelta

import flyte

from _common import image, sleep_env, sleep_leaf

env = flyte.TaskEnvironment(
    name="bench_long_chain",
    image=image,
    resources=flyte.Resources(cpu=1, memory="1Gi"),
    depends_on=[sleep_env],
)


@env.task
async def chain(length: int = 100, sleep_seconds: int = 0) -> int:
    print(f"chain length={length}", flush=True)
    for i in range(length):
        await sleep_leaf(seconds=timedelta(seconds=sleep_seconds))  # awaited in series, one node at a time
    return length


if __name__ == "__main__":
    flyte.init_from_config()
    r = flyte.with_runcontext("remote").run(chain, length=100, sleep_seconds=0)
    print(r.url)
