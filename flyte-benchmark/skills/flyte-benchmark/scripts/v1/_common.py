"""Shared image + core-sleep leaf for the Flyte **v1** (flytekit) workloads.

Leaves are core-sleep tasks so they run with no task pod — same as the v2 suite,
so what you measure is flytepropeller's control-plane cost, not pod startup.

The core-sleep flytekit plugin is not on PyPI yet; it lives on a public fork
branch, and a prebuilt, anonymously-pullable image already exists. Both are
overridable by env if you want to build your own:

    FLYTE_BENCH_V1_IMAGE     full image ref to use as-is (default: the prebuilt one)
    FLYTE_BENCH_V1_REGISTRY  registry to build+push a fresh ImageSpec into
"""

import os
from datetime import timedelta
from typing import List

import flytekit as fl
from flytekit import dynamic, task
from flytekitplugins.sleep import Sleep

_PREBUILT = os.getenv(
    "FLYTE_BENCH_V1_IMAGE", "ghcr.io/machichima/sleep-fanout:2ycwzkpzuK3eMFlr0R7oYA"
)
_REGISTRY = os.getenv("FLYTE_BENCH_V1_REGISTRY")

# Default to the prebuilt tag: it needs no push access and the cluster can pull
# it anonymously. Set FLYTE_BENCH_V1_REGISTRY to build the image yourself.
sleep_image = (
    fl.ImageSpec(
        registry=_REGISTRY,
        name="sleep-fanout",
        apt_packages=["git"],
        packages=[
            "git+https://github.com/machichima/flytekit.git"
            "@add-sleep-plugin#subdirectory=plugins/flytekit-sleep"
        ],
    )
    if _REGISTRY
    else _PREBUILT
)


@task(container_image=sleep_image)
def make_durations(duration: timedelta, n: int) -> List[timedelta]:
    """Build the per-leaf duration list that a map_task would fan out over."""
    return [duration] * n


@task(task_config=Sleep(), container_image=sleep_image)
def sleep_leaf(duration: timedelta) -> None:
    # core-sleep leaf: backend sleeps, no pod, no output.
    pass


@dynamic(container_image=sleep_image)
def fan_leaves(n: int, duration: timedelta) -> int:
    """Emit `n` parallel core-sleep leaves inside ONE dynamic subworkflow.

    map_task + core-sleep does not work (the backend plugin rejects ArrayNode
    inputs: "input [duration] must be typed as duration"). Emitting n discrete
    leaf nodes from a @dynamic gives the same wide fan-out and is the more
    faithful v1 stress anyway: every leaf is a real node accreted into the single
    workflow CRD, which is exactly the v1 behaviour under test.
    """
    for _ in range(n):
        sleep_leaf(duration=duration)
    return n


@dynamic(container_image=sleep_image)
def fan_leaves_secs(n: int, seconds: int) -> int:
    """Like fan_leaves, but builds the duration inside the dynamic — a @workflow
    can't call timedelta() on a Promise input."""
    duration = timedelta(seconds=seconds)
    for _ in range(n):
        sleep_leaf(duration=duration)
    return n
