"""Generic benchmark driver: submit one workload, poll to terminal, record timing.

Usage:
  python _runner.py <workload> [k=v ...]
Workloads: fanout concurrency nested long_chain
Emits a JSON line prefixed with RESULT_JSON: for the report generator to scrape.
"""
import json
import sys
import time
import traceback

import flyte
from flyte.remote import Run

import os
CONFIG = os.getenv("FLYTE_BENCH_CONFIG", os.path.expanduser("~/.flyte/config.yaml"))
POLL_TIMEOUT = int(os.getenv("BENCH_TIMEOUT", "1200"))  # seconds


def poll_to_terminal(run_name, deadline):
    """Re-fetch the run until done() or deadline. Returns (phase_str, timed_out)."""
    interval = 3.0
    while True:
        r = Run.get(name=run_name)
        if r.done():
            return str(r.phase), False
        if time.time() > deadline:
            return str(r.phase), True
        time.sleep(interval)
        interval = min(interval * 1.3, 15.0)


def load(workload):
    if workload == "fanout":
        from fanout import fanout
        return fanout
    if workload == "concurrency":
        from concurrency import hold
        return hold
    if workload == "nested":
        from nested import level
        return level
    if workload == "long_chain":
        from long_chain import chain
        return chain
    raise ValueError(f"unknown workload {workload}")


def coerce(v):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def main():
    workload = sys.argv[1]
    params = {}
    for arg in sys.argv[2:]:
        k, _, v = arg.partition("=")
        params[k] = coerce(v)

    flyte.init_from_config(CONFIG)
    fn = load(workload)

    result = {"workload": workload, "params": params}
    t0 = time.time()
    result["submit_ts"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0))
    try:
        run = flyte.with_runcontext("remote").run(fn, **params)
        submit_done = time.time()
        result["build_submit_seconds"] = round(submit_done - t0, 1)
        result["url"] = run.url
        run_name = run.name
        print(f"SUBMITTED {workload} url={run.url} name={run_name} (build+submit {result['build_submit_seconds']}s)", flush=True)
        deadline = submit_done + POLL_TIMEOUT
        phase, timed_out = poll_to_terminal(run_name, deadline)
        t_end = time.time()
        result["wall_seconds"] = round(t_end - t0, 1)
        result["exec_seconds"] = round(t_end - submit_done, 1)
        result["phase"] = phase
        result["timed_out"] = timed_out
    except Exception as e:
        result["phase"] = "DRIVER_ERROR"
        result["error"] = f"{type(e).__name__}: {e}"
        result["wall_seconds"] = round(time.time() - t0, 1)
        traceback.print_exc()
    print("RESULT_JSON:" + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
