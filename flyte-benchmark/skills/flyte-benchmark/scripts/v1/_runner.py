"""Flyte **v1** benchmark driver: submit one workload, poll to terminal, time it.

Usage:
  python _runner.py <workload> [--flag value ...]
Workloads: fanout concurrency nested long_chain

Submits via `pyflyte run --remote` (registers + launches), then polls the
execution through FlyteRemote until terminal and emits a RESULT_JSON: line — the
same line shape the v2 driver emits, so both feed plot_results.py.

Durations use flytekit's form, e.g. --sleep_duration 0s.

Env:
  FLYTE_BENCH_CONFIG   flytekit config file      (default: ./config.yaml)
  FLYTE_BENCH_PROJECT  project                   (default: flytesnacks)
  FLYTE_BENCH_DOMAIN   domain                    (default: development)
  BENCH_MAX_PARALLELISM  per-execution parallelism (default: 1000 — see below)
  BENCH_TIMEOUT        poll timeout in seconds   (default: 1800)
"""
import json
import os
import re
import sys
import time

# Pin a default image before pyflyte is imported. Every task here overrides its
# own image, but if the `union` flytekit plugin is installed it tries to resolve a
# default image at import time and crashes on newer Pythons; this short-circuits
# that lookup.
os.environ.setdefault("FLYTE_INTERNAL_IMAGE",
                      os.getenv("FLYTE_BENCH_V1_IMAGE",
                                "ghcr.io/machichima/sleep-fanout:2ycwzkpzuK3eMFlr0R7oYA"))

HERE = os.path.dirname(os.path.realpath(__file__))
CONFIG = os.getenv("FLYTE_BENCH_CONFIG", os.path.join(HERE, "config.yaml"))
PROJECT = os.getenv("FLYTE_BENCH_PROJECT", "flytesnacks")
DOMAIN = os.getenv("FLYTE_BENCH_DOMAIN", "development")
POLL_TIMEOUT = int(os.getenv("BENCH_TIMEOUT", "1800"))

WORKLOADS = {"fanout", "concurrency", "nested", "long_chain"}


def submit(workload, cli_args):
    """Run `pyflyte run --remote`, return the execution id parsed from its output."""
    from click.testing import CliRunner
    from flytekit.clis.sdk_in_container import pyflyte

    path = os.path.join(HERE, f"{workload}.py")
    # --max-parallelism 1000 to match the v2 SDK default. flytepropeller defaults
    # to ~25, which throttles wide fan-outs and would make v1 look slower for a
    # reason that has nothing to do with its control plane.
    max_par = os.getenv("BENCH_MAX_PARALLELISM", "1000")
    args = ["--config", CONFIG, "run", "--remote", "--max-parallelism", max_par,
            "--project", PROJECT, "--domain", DOMAIN, path, "wf", *cli_args]
    res = CliRunner().invoke(pyflyte.main, args)
    print(res.output, flush=True)
    if res.exception:
        raise res.exception
    # pyflyte prints a console URL ending in /executions/<id>
    m = re.search(r"/executions/([a-z0-9]+)", res.output)
    if not m:
        raise RuntimeError("could not parse execution id from pyflyte output")
    return m.group(1)


def _phase_name(ph):
    from flytekit.models.core.execution import WorkflowExecutionPhase as P
    try:
        return P.enum_to_string(int(ph))
    except Exception:
        return str(ph)


def poll_to_terminal(exec_id, deadline):
    from flytekit.configuration import Config
    from flytekit.remote import FlyteRemote

    remote = FlyteRemote(Config.auto(config_file=CONFIG), default_project=PROJECT, default_domain=DOMAIN)
    interval = 3.0
    while True:
        ex = remote.sync_execution(remote.fetch_execution(name=exec_id))
        if ex.is_done:
            err = ex.closure.error.message if ex.closure.error else None
            return _phase_name(ex.closure.phase), False, err
        if time.time() > deadline:
            return _phase_name(ex.closure.phase), True, None
        time.sleep(interval)
        interval = min(interval * 1.3, 15.0)


def main():
    workload = sys.argv[1]
    if workload not in WORKLOADS:
        raise ValueError(f"unknown workload {workload}; pick from {sorted(WORKLOADS)}")
    cli_args = sys.argv[2:]  # passed straight through to pyflyte (e.g. --n_children 1000)

    result = {"workload": workload, "args": cli_args, "system": "v1"}
    t0 = time.time()
    result["submit_ts"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0))
    try:
        exec_id = submit(workload, cli_args)
        submit_done = time.time()
        result["build_submit_seconds"] = round(submit_done - t0, 1)
        result["exec_id"] = exec_id
        print(f"SUBMITTED {workload} exec_id={exec_id} (build+submit {result['build_submit_seconds']}s)", flush=True)
        phase, timed_out, err = poll_to_terminal(exec_id, submit_done + POLL_TIMEOUT)
        t_end = time.time()
        result["wall_seconds"] = round(t_end - t0, 1)
        result["exec_seconds"] = round(t_end - submit_done, 1)
        result["phase"] = phase
        result["timed_out"] = timed_out
        if err:
            result["error"] = err[:500]
    except Exception as e:
        import traceback
        result["phase"] = "DRIVER_ERROR"
        result["error"] = f"{type(e).__name__}: {e}"
        result["wall_seconds"] = round(time.time() - t0, 1)
        traceback.print_exc()
    print("RESULT_JSON:" + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
