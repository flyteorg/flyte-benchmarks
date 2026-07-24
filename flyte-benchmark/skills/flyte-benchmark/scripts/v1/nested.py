"""Depth (v1) — deep nested subworkflows.

A @dynamic recurses `depth` levels, fanning out `width` leaves at each level.
In v1 this accretes node state into the parent workflow CRD and pays a reconcile
round-trip per level.

Sweep depth: 20 -> 50.
"""

from datetime import timedelta

from flytekit import dynamic, workflow

from _common import sleep_image, sleep_leaf


@dynamic(container_image=sleep_image)
def nested(depth: int, width: int, duration: timedelta) -> int:
    for _ in range(width):
        sleep_leaf(duration=duration)
    if depth <= 0:
        return 0
    return nested(depth=depth - 1, width=width, duration=duration)


@workflow
def wf(depth: int = 20, width: int = 5, sleep_duration: timedelta = timedelta(seconds=0)) -> int:
    return nested(depth=depth, width=width, duration=sleep_duration)
