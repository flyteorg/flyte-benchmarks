"""Shared image + leaf env for the benchmark workloads.

Leaves use the core-sleep plugin so they run in the data plane with no task pod —
we fan out wide without paying pod-startup cost. Registry is taken from env so
remote runs can redirect image builds to a writable repo you control.
"""

import os
from datetime import timedelta

import flyte
from flyte.extras import Sleep

# Default to the existing public ghcr.io/flyteorg/flyte repo: it's already
# pullable by the cluster (no auth), so pushing benchmark layers there avoids
# the ErrImagePull/401 you get from a fresh private repo. Override via env.
_REGISTRY = os.getenv("FLYTE_STRESS_IMAGE_REGISTRY", "ghcr.io/flyteorg")
_NAME = os.getenv("FLYTE_STRESS_IMAGE_NAME", "flyte")

image = flyte.Image.from_debian_base(
    python_version=(3, 12),
    registry=_REGISTRY,
    name=_NAME,
    platform=("linux/amd64",),
)

# core-sleep leaf: no pod created.
sleep_env = flyte.TaskEnvironment(name="bench_sleep_leaf", image=image, plugin_config=Sleep())


# NOTE: the backend `core-sleep` plugin does not support task outputs
# ("task type [core-sleep] does not support outputs"), so the leaf must not
# return a value. It also REQUIRES its sleep-duration input to be typed as a
# duration ("input [seconds] must be typed as duration") — Python `timedelta`
# maps to the Flyte Duration type, so the input must be a timedelta, not int.
@sleep_env.task
async def sleep_leaf(seconds: timedelta = timedelta(0)) -> None:
    return None
