# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#   "flytekit>=1.13",
#   "flytekitplugins-sleep @ git+https://github.com/machichima/flytekit.git@add-sleep-plugin#subdirectory=plugins/flytekit-sleep",
# ]
# ///
"""Steady-state concurrency (v1) — hold M leaves live for a window.

The fan-out shape with a long sleep, so M leaves stay RUNNING and propeller
reconciles them continuously. Same flags as ../v2/concurrency.py.

    uv run concurrency.py --m 1000 --hold 120
    uv run concurrency.py --m 40000 --hold 120
"""

from flytekit import workflow

from _common import leaves, parser, run_bench


@workflow
def wf(m: int = 1000, hold: int = 120) -> int:
    return leaves(n=m, seconds=hold)


if __name__ == "__main__":
    ap = parser("steady-state concurrency: hold M leaves live")
    ap.add_argument("--m", type=int, default=1000, help="leaves held live")
    ap.add_argument("--hold", type=int, default=120, help="seconds to hold them")
    a = ap.parse_args()
    run_bench("concurrency", __file__, ["--m", str(a.m), "--hold", str(a.hold)],
              {"m": a.m, "hold": a.hold}, total_actions=a.m, timeout=a.timeout)
