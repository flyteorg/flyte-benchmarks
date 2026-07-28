# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#   "flytekit>=1.13",
#   "flytekitplugins-sleep @ git+https://github.com/machichima/flytekit.git@add-sleep-plugin#subdirectory=plugins/flytekit-sleep",
# ]
# ///
"""Wide fan-out (v1) — one workflow, N parallel core-sleep leaves.

v1 grows ONE workflow CRD in etcd until it hits the size/offload limit and
reconcile slows down. Same shape and flags as ../v2/fanout.py.

    uv run fanout.py --n 1000
    uv run fanout.py --n 6000
"""

from flytekit import workflow

from _common import leaves, parser, run_bench


@workflow
def wf(n: int = 1000, sleep: int = 0) -> int:
    return leaves(n=n, seconds=sleep)


if __name__ == "__main__":
    ap = parser("wide fan-out: one workflow, N parallel leaves")
    ap.add_argument("--n", type=int, default=1000, help="leaves in the workflow")
    ap.add_argument("--sleep", type=int, default=0, help="seconds each leaf sleeps")
    a = ap.parse_args()
    run_bench("fanout", __file__, ["--n", str(a.n), "--sleep", str(a.sleep)],
              {"n": a.n, "sleep": a.sleep}, total_actions=a.n, timeout=a.timeout)
