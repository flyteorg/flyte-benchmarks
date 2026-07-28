# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#   "flytekit>=1.13",
#   "flytekitplugins-sleep @ git+https://github.com/machichima/flytekit.git@add-sleep-plugin#subdirectory=plugins/flytekit-sleep",
# ]
# ///
"""Long chain (v1) — N nodes in one workflow, in series.

Node state accumulates over many transitions inside a single workflow CRD. Same
shape and flags as ../v2/long_chain.py.

    uv run long_chain.py --length 100
    uv run long_chain.py --length 500
"""

from flytekit import workflow

from _common import chained_leaves, parser, run_bench


@workflow
def wf(length: int = 100, sleep: int = 0) -> int:
    return chained_leaves(length=length, seconds=sleep)


if __name__ == "__main__":
    ap = parser("long chain: N nodes in series")
    ap.add_argument("--length", type=int, default=100, help="nodes in the chain")
    ap.add_argument("--sleep", type=int, default=0, help="seconds each node sleeps")
    a = ap.parse_args()
    run_bench("long_chain", __file__, ["--length", str(a.length), "--sleep", str(a.sleep)],
              {"length": a.length, "sleep": a.sleep}, total_actions=a.length, timeout=a.timeout)
