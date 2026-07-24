"""Swarm (v1) — K workflows each holding `m` leaves RUNNING for `hold_seconds`.

Mirrors the v2 swarm (K runs x n_children) so the two planes compare at the same
total held-task count (K * m).

Registration happens once via `_runner.submit` (pyflyte registers + launches
execution #1); the remaining K-1 are launched through FlyteRemote.execute on the
resulting launch plan — a cheap create-execution call, so K can get large without
re-running pyflyte per workflow.

Emits RESULT_JSON: {k, m, total_held, succeeded, wall_seconds, timed_out}.
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)

from _runner import CONFIG, DOMAIN, POLL_TIMEOUT, PROJECT, submit  # noqa: E402


def _remote():
    from flytekit.configuration import Config
    from flytekit.remote import FlyteRemote
    return FlyteRemote(Config.auto(config_file=CONFIG), default_project=PROJECT, default_domain=DOMAIN)


def _terminal(remote, exec_id):
    """Return (done, succeeded) for one execution."""
    from flytekit.models.core.execution import WorkflowExecutionPhase as P
    ex = remote.sync_execution(remote.fetch_execution(name=exec_id))
    if ex.is_done:
        return True, ex.closure.phase == P.SUCCEEDED
    return False, False


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10, help="number of workflows")
    ap.add_argument("--m", type=int, default=1000, help="held leaves per workflow")
    ap.add_argument("--hold_seconds", type=int, default=120)
    ap.add_argument("--launch_workers", type=int, default=32)
    args = ap.parse_args()

    t0 = time.time()
    result = {"system": "v1", "workload": "swarm", "k": args.k, "m": args.m,
              "total_held": args.k * args.m, "hold_seconds": args.hold_seconds}

    # 1. register + launch #1 via pyflyte
    first = submit("concurrency", ["--m", str(args.m), "--hold_seconds", str(args.hold_seconds)])
    print(f"registered + launched #1 exec={first}", flush=True)

    remote = _remote()
    # 2. resolve the launch plan pyflyte registered for this execution
    ex1 = remote.fetch_execution(name=first)
    lp_id = ex1.spec.launch_plan
    lp = remote.fetch_launch_plan(name=lp_id.name, version=lp_id.version, project=PROJECT, domain=DOMAIN)
    print(f"launch plan {lp_id.name}:{lp_id.version}; fanning out {args.k - 1} more", flush=True)

    # 3. launch the remaining K-1 concurrently.
    # max_parallelism on EVERY execution, not just #1: pyflyte set it on exec #1
    # only, and a re-executed LP falls back to propeller's ~25, which would
    # throttle these fan-outs and inflate the v1 makespan unfairly.
    from flytekit import Options
    opts = Options(max_parallelism=int(os.getenv("BENCH_MAX_PARALLELISM", "1000")))

    def launch(_i):
        e = _remote().execute(lp, inputs={"m": args.m, "hold_seconds": args.hold_seconds},
                              wait=False, options=opts)
        return e.id.name

    exec_ids = [first]
    with ThreadPoolExecutor(max_workers=args.launch_workers) as pool:
        exec_ids.extend(pool.map(launch, range(args.k - 1)))
    submit_done = time.time()
    result["build_submit_seconds"] = round(submit_done - t0, 1)
    print(f"launched {len(exec_ids)} workflows in {result['build_submit_seconds']}s", flush=True)

    # 4. poll all to terminal
    deadline = submit_done + POLL_TIMEOUT
    pending = set(exec_ids)
    succeeded = 0
    while pending and time.time() < deadline:
        time.sleep(10)
        with ThreadPoolExecutor(max_workers=args.launch_workers) as pool:
            states = list(pool.map(lambda eid: (eid,) + _terminal(_remote(), eid), pending))
        for eid, done, ok in states:
            if done:
                pending.discard(eid)
                succeeded += int(ok)
        print(f"  {time.strftime('%T')} terminal={len(exec_ids) - len(pending)}/{len(exec_ids)} "
              f"succeeded={succeeded}", flush=True)

    result["succeeded"] = succeeded
    result["timed_out"] = bool(pending)
    result["wall_seconds"] = round(time.time() - t0, 1)
    print("RESULT_JSON:" + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
