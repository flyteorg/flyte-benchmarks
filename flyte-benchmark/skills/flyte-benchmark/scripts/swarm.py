"""Workload 5 — many concurrent runs (the realistic multi-pipeline shape).

Instead of one giant run, fire K independent runs at once, each a 2000-wide
fan-out of 1s core-sleep leaves. Target: 100 runs x 2000 actions = 200k actions
in flight. This stresses the v2 control plane / actions-service at run-level
concurrency, which is how real platforms get loaded (many users/pipelines firing
together) — not one pathologically wide or deep run.

A horizontally-scaled / distributed-store-backed plane handles 100x2000; this is
to find where a single-pod OSS v2 executor starts to break. Ramp K upward from 2
and watch for: run failures, submit/poll timeouts, control-plane OOM, or
action-scheduling backlog.

The parent `wide` task is deliberately lean (512Mi) so the limit we hit is the
control plane, not node memory for K parent pods. The 2000 leaves are core-sleep
(no pod).

  python swarm.py --k 2 --n_children 2000 --sleep_seconds 1
  python swarm.py --k 100 --n_children 2000 --sleep_seconds 1   # the target
"""

import argparse
import asyncio
import json
import os
import time
import traceback
from datetime import timedelta

import flyte
from flyte.remote import Run

from _common import image, sleep_env, sleep_leaf

CONFIG = os.getenv("FLYTE_BENCH_CONFIG", os.path.expanduser("~/.flyte/config.yaml"))

swarm_env = flyte.TaskEnvironment(
    name="bench_swarm",
    image=image,
    # lean on purpose: parent only fires leaves and awaits, so K parent pods
    # don't make node memory the bottleneck before the control plane is.
    # Small request (packs many parents per node) with burst headroom — at K=100
    # this is ~25 CPU of requests, well within the worker ASG autoscaler maxes.
    resources=flyte.Resources(cpu=("800m", "1"), memory=("800Mi", "1Gi")),
    depends_on=[sleep_env],
)


@swarm_env.task
async def wide(n_children: int = 2000, sleep_seconds: int = 1) -> int:
    await asyncio.gather(*(sleep_leaf(seconds=timedelta(seconds=sleep_seconds)) for _ in range(n_children)))
    return n_children


async def _submit_one(n_children, sleep_seconds):
    """Submit one remote run; return its name or raise."""
    run = await flyte.with_runcontext("remote", overwrite_cache=True).run.aio(wide, n_children=n_children, sleep_seconds=sleep_seconds)
    return run.name, run.url


def _poll_all(names, deadline):
    """Poll all runs to terminal. Returns dict name->phase and a timed_out flag."""
    if not names:                      # no runs submitted (all submits errored) — don't crash
        return {}, False
    phases = {}
    pending = set(names)
    interval = 3.0
    while pending:
        for name in list(pending):
            # tolerate transient API/gateway errors (504s under heavy load) —
            # skip this run this cycle and retry next, don't kill the whole poll.
            try:
                r = Run.get(name=name)
            except Exception:
                continue
            if r.done():
                phases[name] = str(r.phase)
                pending.discard(name)
        if not pending:
            return phases, False
        if time.time() > deadline:
            for name in pending:
                r = Run.get(name=name)
                phases[name] = str(r.phase) + "(TIMED_OUT)"
            return phases, True
        time.sleep(interval)
        interval = min(interval * 1.3, 15.0)


async def _submit_batch(count, n_children, sleep_seconds):
    """Submit `count` remote runs concurrently; return (names, submit_errors)."""
    subs = await asyncio.gather(
        *(_submit_one(n_children, sleep_seconds) for _ in range(count)), return_exceptions=True
    )
    names, errs = [], 0
    for s in subs:
        if isinstance(s, Exception):
            errs += 1
            print(f"submit error: {type(s).__name__}: {s}", flush=True)  # surface, don't swallow
        else:
            names.append(s[0])
    return names, errs


async def _amain(k, n_children, sleep_seconds, timeout, max_retries):
    """Submit K runs; relaunch FAILED runs up to `max_retries` extra rounds so that
    transient failures (e.g. a launch-burst DEADLINE_EXCEEDED) don't count as
    permanent. The SAME policy applies to every cluster, so the comparison stays fair:
    identical target (K workflows x n_children tasks) and identical retry budget on both.
    We report both first-pass success (raw transient rate) and final success (after retries)."""
    flyte.init_from_config(CONFIG)
    result = {"workload": "swarm", "k": k, "n_children": n_children, "sleep_seconds": sleep_seconds,
              "total_actions": k * n_children, "max_retries": max_retries}
    t0 = time.time()
    result["submit_ts"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0))

    succeeded = 0                 # cumulative successful runs toward the target of K
    first_pass_succeeded = 0
    total_runs_submitted = 0      # includes relaunches — reported for transparency
    total_submit_errors = 0
    rounds_used = 0
    timed_out = False
    for rnd in range(max_retries + 1):
        need = k - succeeded      # (re)launch exactly the shortfall
        if need <= 0:
            break
        names, errs = await _submit_batch(need, n_children, sleep_seconds)
        total_runs_submitted += len(names)
        total_submit_errors += errs
        phases, timed_out = _poll_all(names, time.time() + timeout)
        s = sum(1 for p in phases.values() if "SUCCEEDED" in p)
        succeeded += s
        rounds_used = rnd
        tag = "SUBMIT" if rnd == 0 else f"RELAUNCH#{rnd}"
        print(f"{tag}: {len(names)} runs, {s} succeeded ({succeeded}/{k} total)", flush=True)
        if rnd == 0:
            first_pass_succeeded = s
            result["first_pass_submitted"] = len(names)
        if timed_out:             # don't keep relaunching if we're blowing the wall-clock
            break

    result["wall_seconds"] = round(time.time() - t0, 1)
    result["timed_out"] = timed_out
    result["total_runs_submitted"] = total_runs_submitted
    result["submit_errors"] = total_submit_errors
    result["first_pass_succeeded"] = first_pass_succeeded          # before any relaunch
    result["first_pass_failed"] = k - first_pass_succeeded         # raw transient-failure count
    result["final_succeeded"] = succeeded                          # after relaunches
    result["failed"] = k - succeeded                               # permanent failures
    result["retry_rounds_used"] = rounds_used
    # keep legacy fields so existing result readers/reports don't break
    result["submitted_ok"] = result.get("first_pass_submitted", 0)
    result["succeeded"] = succeeded
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=2, help="number of concurrent runs (target successes)")
    ap.add_argument("--n_children", type=int, default=2000, help="leaves per run")
    ap.add_argument("--sleep_seconds", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=int(os.getenv("BENCH_TIMEOUT", "1800")))
    ap.add_argument("--max-retries", type=int, default=int(os.getenv("SWARM_MAX_RETRIES", "0")),
                    help="extra rounds to relaunch FAILED runs (same on every cluster for fairness). "
                         "0 = submit once, no relaunch.")
    args = ap.parse_args()

    result = {}
    try:
        result = asyncio.run(_amain(args.k, args.n_children, args.sleep_seconds, args.timeout, args.max_retries))
    except Exception as e:
        result = {"workload": "swarm", "k": args.k, "phase": "DRIVER_ERROR",
                  "error": f"{type(e).__name__}: {e}"}
        traceback.print_exc()
    print("RESULT_JSON:" + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
