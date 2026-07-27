"""Shared pieces for the Flyte v2 benchmark scripts.

Holds the core-sleep leaf (leaves run with no task pod, so what you measure is
orchestration cost) and the submit → poll → `RESULT_JSON:` driver every script
ends with. The four scripts next to this file are the benchmarks; this is only
their plumbing.

Env:
  FLYTE_BENCH_CONFIG           config for the cluster under test (default ~/.flyte/config.yaml)
  FLYTE_BENCH_IMAGE_REGISTRY   registry for the task image      (default ghcr.io/flyteorg)
  FLYTE_BENCH_IMAGE_NAME       image name                       (default flyte)
"""

import argparse
import asyncio
import json
import os
import time
import traceback
from datetime import timedelta

import flyte
from flyte.extras import Sleep
from flyte.remote import Run

CONFIG = os.getenv("FLYTE_BENCH_CONFIG", os.path.expanduser("~/.flyte/config.yaml"))

# Default to the public ghcr.io/flyteorg/flyte repo: the cluster can already pull
# it, which avoids the ErrImagePull/401 a fresh private repo gives you.
image = flyte.Image.from_debian_base(
    python_version=(3, 12),
    registry=os.getenv("FLYTE_BENCH_IMAGE_REGISTRY", "ghcr.io/flyteorg"),
    name=os.getenv("FLYTE_BENCH_IMAGE_NAME", "flyte"),
    platform=("linux/amd64",),
)

# core-sleep leaf: the backend sleeps, no pod is created.
sleep_env = flyte.TaskEnvironment(name="bench_sleep_leaf", image=image, plugin_config=Sleep())


# The core-sleep plugin supports no task outputs ("task type [core-sleep] does
# not support outputs"), so the leaf returns None. It also requires its input
# typed as a duration, so a plain int will not do.
@sleep_env.task
async def sleep_leaf(seconds: timedelta = timedelta(0)) -> None:
    return None


def task_env(name):
    """Parent environment for one benchmark shape."""
    return flyte.TaskEnvironment(
        name=name,
        image=image,
        resources=flyte.Resources(cpu=(1, 2), memory=("2Gi", "4Gi")),
        depends_on=[sleep_env],
    )


async def leaves(n, seconds):
    """Fan out `n` core-sleep leaves in parallel."""
    await asyncio.gather(*(sleep_leaf(seconds=timedelta(seconds=seconds)) for _ in range(n)))


def parser(description):
    """Argument parser carrying the flags every script shares."""
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--timeout", type=int, default=int(os.getenv("BENCH_TIMEOUT", "1800")),
                    help="seconds to wait for the run(s) to reach a terminal phase")
    return ap


def _poll(names, deadline):
    """Poll runs to terminal. Returns (succeeded, failed, timed_out)."""
    pending, succeeded = set(names), 0
    interval = 3.0
    while pending:
        for name in list(pending):
            try:
                r = Run.get(name=name)
            except Exception:
                continue          # transient API error under load — retry next cycle
            if r.done():
                pending.discard(name)
                succeeded += "SUCCEEDED" in str(r.phase)
        if not pending:
            break
        if time.time() > deadline:
            return succeeded, len(names) - succeeded, True
        time.sleep(interval)
        interval = min(interval * 1.3, 15.0)
    return succeeded, len(names) - succeeded, False


def _submit(fn, params, k):
    if k == 1:
        return [flyte.with_runcontext("remote").run(fn, **params)]

    async def submit_all():
        ctx = flyte.with_runcontext("remote", overwrite_cache=True)
        return await asyncio.gather(*(ctx.run.aio(fn, **params) for _ in range(k)))

    return list(asyncio.run(submit_all()))


def run_bench(workload, fn, params, total_actions, timeout=1800, k=1):
    """Submit `k` copies of fn(**params), wait for all, print a RESULT_JSON: line.

    k=1 for the single-run shapes; swarm.py passes k>1 to fire K runs at once.
    Failed runs are reported, never relaunched — a retry budget would make two
    clusters incomparable unless both used the same one.
    """
    flyte.init_from_config(CONFIG)
    result = {"workload": workload, "system": "v2", "params": params, "k": k,
              "total_actions": total_actions}
    t0 = time.time()
    result["submit_ts"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0))
    try:
        runs = _submit(fn, params, k)
        submit_done = time.time()
        result["build_submit_seconds"] = round(submit_done - t0, 1)
        result["url"] = runs[0].url
        print(f"SUBMITTED {workload} x{k} url={runs[0].url} "
              f"(build+submit {result['build_submit_seconds']}s)", flush=True)

        succeeded, failed, timed_out = _poll([r.name for r in runs], submit_done + timeout)
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
