"""Shared pieces for the Flyte **v1** (flytekit) benchmark scripts.

Holds the core-sleep leaf and fan-out building blocks, plus the register →
launch → poll → `RESULT_JSON:` driver. The four scripts next to this file are
the benchmarks; this is only their plumbing. They mirror the v2 scripts flag for
flag, so the same command line compares planes.

The core-sleep flytekit plugin is not on PyPI yet; it lives on a public fork
branch, and a prebuilt, anonymously-pullable image already exists.

The cluster under test comes from flytekit's own config discovery — point
`FLYTECTL_CONFIG` at a config file, or let it find `~/.flyte/config.yaml`.

Env:
  FLYTE_BENCH_PROJECT      project             (default: flytesnacks)
  FLYTE_BENCH_DOMAIN       domain              (default: development)
  BENCH_MAX_PARALLELISM    per-execution parallelism (default: 1000 — see below)
  FLYTE_BENCH_V1_IMAGE     task image to use as-is
  FLYTE_BENCH_V1_REGISTRY  registry to build a fresh ImageSpec into instead
"""

import argparse
import json
import os
import re
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import flytekit as fl
from flytekit import dynamic, task

from flytekitplugins.sleep import Sleep

PROJECT = os.getenv("FLYTE_BENCH_PROJECT", "flytesnacks")
DOMAIN = os.getenv("FLYTE_BENCH_DOMAIN", "development")
MAX_PARALLELISM = int(os.getenv("BENCH_MAX_PARALLELISM", "1000"))

_PREBUILT = os.getenv("FLYTE_BENCH_V1_IMAGE",
                      "ghcr.io/machichima/sleep-fanout:2ycwzkpzuK3eMFlr0R7oYA")
_REGISTRY = os.getenv("FLYTE_BENCH_V1_REGISTRY")

# Every task overrides its image, but the `union` flytekit plugin (if installed)
# resolves a default image at import time and crashes on newer Pythons. Pinning
# this short-circuits that lookup. Must happen before pyflyte is imported.
os.environ.setdefault("FLYTE_INTERNAL_IMAGE", _PREBUILT)

# Default to the prebuilt tag: it needs no push access and the cluster can pull
# it anonymously. Set FLYTE_BENCH_V1_REGISTRY to build the image yourself.
sleep_image = (
    fl.ImageSpec(
        registry=_REGISTRY,
        name="sleep-fanout",
        apt_packages=["git"],
        packages=["git+https://github.com/machichima/flytekit.git"
                  "@add-sleep-plugin#subdirectory=plugins/flytekit-sleep"],
    )
    if _REGISTRY
    else _PREBUILT
)


@task(task_config=Sleep(), container_image=sleep_image)
def sleep_leaf(duration: timedelta) -> None:
    # core-sleep leaf: the backend sleeps, no pod, no output.
    pass


@dynamic(container_image=sleep_image)
def leaves(n: int, seconds: int) -> int:
    """Emit `n` parallel core-sleep leaves inside ONE dynamic subworkflow.

    map_task + core-sleep does not work (the backend plugin rejects ArrayNode
    inputs), and this is the more faithful v1 stress anyway: every leaf is a real
    node accreted into the single workflow CRD, which is the v1 behaviour under
    test. The duration is built here because a @workflow can't call timedelta()
    on a Promise input.
    """
    duration = timedelta(seconds=seconds)
    for _ in range(n):
        sleep_leaf(duration=duration)
    return n


@dynamic(container_image=sleep_image)
def chained_leaves(length: int, seconds: int) -> int:
    """`length` leaves chained sequentially (`prev >> cur`)."""
    duration = timedelta(seconds=seconds)
    prev = None
    for _ in range(length):
        cur = sleep_leaf(duration=duration)
        if prev is not None:
            prev >> cur                     # force sequential ordering
        prev = cur
    return length


def parser(description):
    """Argument parser carrying the flags every script shares."""
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--timeout", type=int, default=int(os.getenv("BENCH_TIMEOUT", "1800")),
                    help="seconds to wait for the execution(s) to finish")
    return ap


def _remote():
    from flytekit.configuration import Config
    from flytekit.remote import FlyteRemote
    # Config.auto() with no file: FLYTECTL_CONFIG, then ~/.flyte/config.yaml.
    return FlyteRemote(Config.auto(), default_project=PROJECT, default_domain=DOMAIN)


def _pyflyte_launch(script, cli_args):
    """`pyflyte run --remote` the given script's `wf`; return the execution id."""
    from click.testing import CliRunner
    from flytekit.clis.sdk_in_container import pyflyte

    # --max-parallelism to match the v2 SDK default. flytepropeller defaults to
    # ~25, which throttles wide fan-outs for a reason unrelated to its control
    # plane and would make the comparison unfair.
    args = ["run", "--remote",
            "--max-parallelism", str(MAX_PARALLELISM),
            "--project", PROJECT, "--domain", DOMAIN, script, "wf", *cli_args]
    res = CliRunner().invoke(pyflyte.main, args)
    print(res.output, flush=True)
    if res.exception:
        raise res.exception
    m = re.search(r"/executions/([a-z0-9]+)", res.output)   # printed console URL
    if not m:
        raise RuntimeError("could not parse execution id from pyflyte output")
    return m.group(1)


def _launch_more(first, k, inputs):
    """Fan out K-1 more executions on the launch plan pyflyte just registered.

    A create-execution call is far cheaper than re-running pyflyte per run, so K
    can get large. max_parallelism has to be set on each one: pyflyte set it on
    the first execution only, and a re-executed launch plan would otherwise fall
    back to propeller's default.
    """
    from flytekit import Options

    remote = _remote()
    lp_id = remote.fetch_execution(name=first).spec.launch_plan
    lp = remote.fetch_launch_plan(name=lp_id.name, version=lp_id.version,
                                  project=PROJECT, domain=DOMAIN)
    opts = Options(max_parallelism=MAX_PARALLELISM)

    def launch(_i):
        return _remote().execute(lp, inputs=inputs, wait=False, options=opts).id.name

    with ThreadPoolExecutor(max_workers=32) as pool:
        return list(pool.map(launch, range(k - 1)))


def _poll(exec_ids, deadline):
    """Poll executions to terminal. Returns (succeeded, failed, timed_out)."""
    from flytekit.models.core.execution import WorkflowExecutionPhase as P

    pending, succeeded = set(exec_ids), 0
    while pending:
        if time.time() > deadline:
            return succeeded, len(exec_ids) - succeeded, True
        time.sleep(5)
        remote = _remote()
        for eid in list(pending):
            try:
                ex = remote.sync_execution(remote.fetch_execution(name=eid))
            except Exception:
                continue          # transient API error under load — retry next cycle
            if ex.is_done:
                pending.discard(eid)
                succeeded += ex.closure.phase == P.SUCCEEDED
    return succeeded, len(exec_ids) - succeeded, False


def run_bench(workload, script, cli_args, params, total_actions,
              timeout=1800, k=1, inputs=None):
    """Register + launch `k` executions of `script`'s wf, wait, print RESULT_JSON:.

    k=1 for the single-run shapes; swarm.py passes k>1 (and `inputs`, the same
    workflow inputs as a dict, for the launch-plan fan-out). Failed executions
    are reported, never relaunched — a retry budget would make two clusters
    incomparable unless both used the same one.
    """
    result = {"workload": workload, "system": "v1", "params": params, "k": k,
              "total_actions": total_actions}
    t0 = time.time()
    result["submit_ts"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0))
    try:
        exec_ids = [_pyflyte_launch(script, cli_args)]
        if k > 1:
            exec_ids += _launch_more(exec_ids[0], k, inputs or {})
        submit_done = time.time()
        result["build_submit_seconds"] = round(submit_done - t0, 1)
        result["exec_id"] = exec_ids[0]
        print(f"SUBMITTED {workload} x{len(exec_ids)} first={exec_ids[0]} "
              f"(build+submit {result['build_submit_seconds']}s)", flush=True)

        succeeded, failed, timed_out = _poll(exec_ids, submit_done + timeout)
        t_end = time.time()
        result.update(wall_seconds=round(t_end - t0, 1),
                      exec_seconds=round(t_end - submit_done, 1),
                      succeeded=succeeded, failed=failed, timed_out=timed_out)
    except Exception as e:
        result.update(phase="DRIVER_ERROR", error=f"{type(e).__name__}: {e}",
                      wall_seconds=round(time.time() - t0, 1))
        traceback.print_exc()
    print("RESULT_JSON:" + json.dumps(result), flush=True)
    return result
