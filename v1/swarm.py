# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#   "flytekit>=1.13",
#   "flytekitplugins-sleep @ git+https://github.com/machichima/flytekit.git@add-sleep-plugin#subdirectory=plugins/flytekit-sleep",
# ]
# ///
"""Swarm (v1) — K independent workflows at once, each an N-wide fan-out.

The scale test. Execution #1 registers via pyflyte; the remaining K-1 launch on
the resulting launch plan, so K can get large. Same flags as ../v2/swarm.py.

    uv run swarm.py --k 10 --n 2000
    uv run swarm.py --k 100 --n 2000     # 200k actions
"""

from flytekit import workflow

from _common import leaves, parser, run_bench


@workflow
def wf(n: int = 2000, sleep: int = 1) -> int:
    return leaves(n=n, seconds=sleep)


if __name__ == "__main__":
    ap = parser("swarm: K concurrent workflows of an N-wide fan-out")
    ap.add_argument("--k", type=int, default=10, help="concurrent workflows")
    ap.add_argument("--n", type=int, default=2000, help="leaves per workflow")
    ap.add_argument("--sleep", type=int, default=1, help="seconds each leaf sleeps")
    a = ap.parse_args()
    run_bench("swarm", __file__, ["--n", str(a.n), "--sleep", str(a.sleep)],
              {"n": a.n, "sleep": a.sleep}, total_actions=a.k * a.n,
              timeout=a.timeout, k=a.k, inputs={"n": a.n, "sleep": a.sleep})
