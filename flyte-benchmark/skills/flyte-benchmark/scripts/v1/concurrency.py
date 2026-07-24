"""Steady-state concurrency (v1) — hold M leaves in-flight for a window.

Same fan-out shape as fanout.py, but with a long sleep so M leaves stay RUNNING
and propeller reconciles them continuously. Watch propeller CPU/mem, reconcile
latency, and the workflow CRD's size in etcd.

Sweep m: 500 -> 5000 -> 20000.
"""

from flytekit import workflow

from _common import fan_leaves_secs


@workflow
def wf(m: int = 500, hold_seconds: int = 120) -> int:
    return fan_leaves_secs(n=m, seconds=hold_seconds)
