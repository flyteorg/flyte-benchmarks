"""Wide fan-out (v1) — one workflow, N parallel core-sleep leaves.

The most discriminating v1-vs-v2 shape: v1 grows ONE workflow CRD in etcd until
it hits the size/offload limit and reconcile slows down. v2 spreads the same work
over per-action CRDs.

Sweep n_children: 1000 -> 6000.
"""

from datetime import timedelta

from flytekit import workflow

from _common import fan_leaves


@workflow
def wf(n_children: int = 1000, sleep_duration: timedelta = timedelta(seconds=0)) -> int:
    return fan_leaves(n=n_children, duration=sleep_duration)
