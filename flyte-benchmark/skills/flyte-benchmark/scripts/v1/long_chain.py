"""Long sequential DAG (v1) — N nodes in one run, in series.

A @dynamic emits `length` sleep leaves chained sequentially (`prev >> cur`), so
node state accumulates over many transitions inside ONE workflow CRD.

Sweep length: 100 -> 500.
"""

from datetime import timedelta

from flytekit import dynamic, workflow

from _common import sleep_image, sleep_leaf


@dynamic(container_image=sleep_image)
def chain(length: int, duration: timedelta) -> int:
    prev = None
    for _ in range(length):
        cur = sleep_leaf(duration=duration)
        if prev is not None:
            prev >> cur  # force sequential ordering (leaves return None)
        prev = cur
    return length


@workflow
def wf(length: int = 100, sleep_duration: timedelta = timedelta(seconds=0)) -> int:
    return chain(length=length, duration=sleep_duration)
