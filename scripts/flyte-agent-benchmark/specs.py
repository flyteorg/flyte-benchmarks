# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""The task suite for the Flyte agent-authoring benchmark.

Each spec is a *framework-agnostic* pipeline task, written in plain natural
language, plus a deterministic oracle: given the exact inputs the harness hands
the agent, we can compute the correct output in plain Python and check what the
agent's pipeline produced. No Flyte import lives here — this file is the ground
truth, runnable on its own (`uv run specs.py` self-tests every oracle).

Two groups:

  A — head-to-head. Expressible in BOTH Flyte v1 (flytekit) and v2 (flyte). These
      give the token / iteration comparison the benchmark is about.
  B — v2 capability. The value-dependent, in-process control-flow patterns v1
      cannot express even with @dynamic (OOM-catch-and-escalate, live-task
      racing, durable checkpointed loops). The v1 arm is expected to record
      `infeasible`; that is itself a result.

Contract with a solution. The harness writes the trial's inputs to `inputs.json`.
The agent's `solution.py` runs its pipeline on those inputs and prints one line:

    TRIAL_OUTPUT_JSON:{...}      # the output dict named in the spec prompt

`oracle.py` reads that dict and calls `check()` below. Inputs are randomized per
trial (seeded), so a hardcoded answer fails — the only reliable way to pass is a
pipeline that actually computes the result.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Spec:
    id: str
    group: str                      # "A" (head-to-head) or "B" (v2 capability)
    difficulty: str                 # easy | medium | hard
    title: str
    # The prompt handed to the agent. Framework-agnostic: it names the data
    # transformation and the output contract, never a Flyte API.
    prompt: str
    output_keys: list[str]          # keys the TRIAL_OUTPUT_JSON must contain
    gen_inputs: Callable[[random.Random], dict]   # deterministic input sampler
    expected: Callable[[dict], dict]              # ground-truth outputs
    # v1 is expected to be unable to express group-B specs. This documents why,
    # and lets the harness score a v1 `infeasible` as the predicted outcome.
    v1_feasible: bool = True
    tol: float = 1e-6               # numeric tolerance for float comparisons

    def check(self, inputs: dict, produced: dict) -> tuple[bool, str]:
        """Grade a produced output dict against the ground truth."""
        want = self.expected(inputs)
        for k in self.output_keys:
            if k not in produced:
                return False, f"missing output key {k!r} (got {sorted(produced)})"
            a, b = produced[k], want[k]
            if isinstance(b, float) or isinstance(a, float):
                try:
                    if abs(float(a) - float(b)) > self.tol:
                        return False, f"{k}: got {a}, want {b}"
                except (TypeError, ValueError):
                    return False, f"{k}: got {a!r}, want {b!r}"
            elif a != b:
                return False, f"{k}: got {a!r}, want {b!r}"
        return True, "ok"


# --------------------------------------------------------------------------- #
# Group A — head-to-head (both arms)
# --------------------------------------------------------------------------- #

def _etl_inputs(r: random.Random) -> dict:
    return {"readings": [r.randint(-20, 100) for _ in range(r.randint(8, 16))]}

def _etl_expected(inp: dict) -> dict:
    kept = [x for x in inp["readings"] if x >= 0]
    mean = round(sum(kept) / len(kept), 3) if kept else 0.0
    return {"count": len(kept), "mean": mean}

ETL = Spec(
    id="etl",
    group="A", difficulty="easy",
    title="Clean-and-aggregate ETL",
    prompt=(
        "Build a pipeline over a list of integer sensor `readings`.\n"
        "  1. Drop every negative reading (keep values >= 0).\n"
        "  2. Compute how many readings were kept and their arithmetic mean.\n"
        "Structure it as more than one step (e.g. a clean step feeding an "
        "aggregate step), passing the cleaned data between steps.\n"
        "Output contract — TRIAL_OUTPUT_JSON with:\n"
        "  count : int   (number of readings kept)\n"
        "  mean  : float (mean of the kept readings, rounded to 3 decimals)"
    ),
    output_keys=["count", "mean"],
    gen_inputs=_etl_inputs, expected=_etl_expected,
)


def _fanout_inputs(r: random.Random) -> dict:
    return {"xs": [r.randint(0, 50) for _ in range(r.randint(6, 12))]}

def _fanout_expected(inp: dict) -> dict:
    return {"squares": [x * x for x in inp["xs"]]}

FANOUT = Spec(
    id="fanout_map",
    group="A", difficulty="easy",
    title="Static fan-out / map",
    prompt=(
        "Given a list of integers `xs`, compute the square of each element in "
        "PARALLEL — one independent task invocation per element (a map / static "
        "fan-out), not a single task that loops internally.\n"
        "Return the squares in the SAME order as the input.\n"
        "Output contract — TRIAL_OUTPUT_JSON with:\n"
        "  squares : list[int]  (xs[i]**2, in order)"
    ),
    output_keys=["squares"],
    gen_inputs=_fanout_inputs, expected=_fanout_expected,
)


def _cond_inputs(r: random.Random) -> dict:
    return {"value": r.randint(0, 100), "threshold": r.randint(30, 70)}

def _cond_expected(inp: dict) -> dict:
    v, t = inp["value"], inp["threshold"]
    return {"result": v * 2 if v >= t else v + 100}

CONDITIONAL = Spec(
    id="conditional",
    group="A", difficulty="medium",
    title="Runtime conditional branch",
    prompt=(
        "Given integers `value` and `threshold`, the pipeline must choose a "
        "branch FROM THE VALUES AT RUNTIME:\n"
        "  - if value >= threshold: run a task that returns value * 2\n"
        "  - otherwise:             run a task that returns value + 100\n"
        "The decision must be made inside the running pipeline (not by the "
        "submitting script). Only the chosen branch's task should run.\n"
        "Output contract — TRIAL_OUTPUT_JSON with:\n"
        "  result : int"
    ),
    output_keys=["result"],
    gen_inputs=_cond_inputs, expected=_cond_expected,
)


def _dyn_inputs(r: random.Random) -> dict:
    return {"seed": r.randint(0, 1000)}

def _dyn_expected(inp: dict) -> dict:
    n = (inp["seed"] % 5) + 3
    return {"n": n, "total": sum(i * i for i in range(n))}

DYNAMIC_FANOUT = Spec(
    id="dynamic_fanout",
    group="A", difficulty="medium",
    title="Data-dependent fan-out",
    prompt=(
        "Two stages, where the width of the second is decided at RUNTIME by the "
        "output of the first:\n"
        "  1. A task reads integer `seed` and returns N = (seed % 5) + 3.\n"
        "  2. Fan out exactly N parallel tasks; the i-th (0-indexed) returns "
        "i*i. Then sum all N results.\n"
        "The number of parallel tasks is NOT known until the first task runs — "
        "it must come from that task's actual output.\n"
        "Output contract — TRIAL_OUTPUT_JSON with:\n"
        "  n     : int  (the computed N)\n"
        "  total : int  (sum of i*i for i in 0..N-1)"
    ),
    output_keys=["n", "total"],
    gen_inputs=_dyn_inputs, expected=_dyn_expected,
)


def _fit_inputs(r: random.Random) -> dict:
    n = r.randint(6, 12)
    xs = [r.randint(0, 20) for _ in range(n)]
    ys = [3 * x + 5 + r.randint(-2, 2) for x in xs]     # noisy line
    return {"x": xs, "y": ys}

def _fit_expected(inp: dict) -> dict:
    x, y = inp["x"], inp["y"]
    n = len(x)
    sx, sy = sum(x), sum(y)
    sxx = sum(v * v for v in x)
    sxy = sum(x[i] * y[i] for i in range(n))
    denom = n * sxx - sx * sx
    m = (n * sxy - sx * sy) / denom
    b = (sy - m * sx) / n
    mse = sum((y[i] - (m * x[i] + b)) ** 2 for i in range(n)) / n
    return {"slope": round(m, 4), "intercept": round(b, 4), "mse": round(mse, 4)}

FIT_EVAL = Spec(
    id="fit_eval",
    group="A", difficulty="hard",
    title="Fit → evaluate (multi-stage, multiple outputs)",
    prompt=(
        "An end-to-end numeric pipeline over paired lists `x` and `y` (equal "
        "length). Use SEPARATE tasks that pass values between them:\n"
        "  1. `fit`: compute the ordinary least-squares line y = m*x + b — return "
        "slope m and intercept b (closed form).\n"
        "  2. `evaluate`: using m and b from step 1, compute the mean squared "
        "error over the same (x, y).\n"
        "Output contract — TRIAL_OUTPUT_JSON with (all rounded to 4 decimals):\n"
        "  slope : float\n  intercept : float\n  mse : float"
    ),
    output_keys=["slope", "intercept", "mse"],
    gen_inputs=_fit_inputs, expected=_fit_expected,
    tol=1e-3,
)


# --------------------------------------------------------------------------- #
# Group B — v2 capability (v1 infeasible)
# --------------------------------------------------------------------------- #

def _oom_inputs(r: random.Random) -> dict:
    # required memory is hidden from the task; the agent must escalate to find it.
    tiers = [256, 512, 1024, 2048]
    return {"required_mb": r.choice(tiers[1:]), "tiers": tiers}

def _oom_expected(inp: dict) -> dict:
    return {"succeeded_at_mb": inp["required_mb"]}

OOM_RETRY = Spec(
    id="oom_retry",
    group="B", difficulty="hard", v1_feasible=False,
    title="Catch OOM, re-run same step with more memory",
    prompt=(
        "A worker task models an out-of-memory failure: it is given an "
        "`allotted_mb` and a hidden `required_mb` (from inputs, but the task must "
        "behave as if it cannot see required_mb ahead of time). If allotted_mb < "
        "required_mb it must raise an out-of-memory error; otherwise it returns "
        "allotted_mb.\n"
        "Drive it from a control task that starts at the SMALLEST tier in "
        "`tiers` and, on an out-of-memory failure, RE-RUNS THE SAME step with the "
        "next larger tier — also overriding the step's memory request to that "
        "tier — until it succeeds. Return the tier it succeeded at.\n"
        "In Flyte v1 this is not expressible: retries are declared statically on "
        "the graph and you cannot catch a live OOM from one node and re-launch "
        "that node with a bigger memory envelope as ordinary control flow. If "
        "your target cannot express it, stop and record the trial as INFEASIBLE.\n"
        "Output contract — TRIAL_OUTPUT_JSON with:\n"
        "  succeeded_at_mb : int  (smallest tier >= required_mb)"
    ),
    output_keys=["succeeded_at_mb"],
    gen_inputs=_oom_inputs, expected=_oom_expected,
)


def _cb_inputs(r: random.Random) -> dict:
    n = r.randint(5, 8)
    # distinct delays so the winner is unambiguous; a few failing indices
    delays = random.Random(r.random()).sample(range(1, 20), n)
    delays = [d / 20.0 for d in delays]                 # 0.05 .. 0.95 s
    fail = sorted(r.sample(range(n), r.randint(1, n - 1)))
    return {"delays": delays, "fail_indices": fail, "max_failures": 2}

def _cb_expected(inp: dict) -> dict:
    # Simulate in time order: first SUCCESS wins; if > max_failures fail first, open (-1).
    order = sorted(range(len(inp["delays"])), key=lambda i: inp["delays"][i])
    failset, failures = set(inp["fail_indices"]), 0
    winner = -1
    for i in order:
        if i in failset:
            failures += 1
            if failures > inp["max_failures"]:
                winner = -1
                break
        else:
            winner = i
            break
    return {"winner": winner}

CIRCUIT_BREAKER = Spec(
    id="circuit_breaker",
    group="B", difficulty="hard", v1_feasible=False,
    title="Race live tasks, cancel losers, open on too many failures",
    prompt=(
        "Launch one task per entry of `delays` CONCURRENTLY. A task whose index "
        "is in `fail_indices` sleeps its delay then raises; otherwise it sleeps "
        "its delay then returns its index.\n"
        "Implement a first-wins race: as results land, the FIRST task to succeed "
        "wins — return its index and cancel the still-pending tasks. But if more "
        "than `max_failures` tasks fail BEFORE any success, open the circuit: "
        "cancel everything and return -1.\n"
        "In Flyte v1 this is not expressible: a task promise is a graph handle, "
        "not an awaitable future — you cannot feed promises to a first-completed "
        "wait, cancel in-flight nodes, or branch on how many have failed so far. "
        "If your target cannot express it, stop and record the trial as "
        "INFEASIBLE.\n"
        "Output contract — TRIAL_OUTPUT_JSON with:\n"
        "  winner : int  (index of first success, or -1 if the circuit opened)"
    ),
    output_keys=["winner"],
    gen_inputs=_cb_inputs, expected=_cb_expected,
)


def _agent_inputs(r: random.Random) -> dict:
    # a program of tool ops over a running accumulator, starting at `start`
    ops = []
    for _ in range(r.randint(4, 7)):
        ops.append(r.choice([["add", r.randint(1, 9)], ["mul", r.randint(2, 4)]]))
    return {"start": r.randint(1, 5), "program": ops}

def _agent_expected(inp: dict) -> dict:
    acc = inp["start"]
    for op, arg in inp["program"]:
        acc = acc + arg if op == "add" else acc * arg
    return {"answer": acc}

AGENT_LOOP = Spec(
    id="agent_loop",
    group="B", difficulty="hard", v1_feasible=False,
    title="Durable checkpointed tool loop",
    prompt=(
        "Build a durable tool-calling loop. Two tools operate on a running "
        "accumulator: `add(acc, k) -> acc+k` and `mul(acc, k) -> acc*k`. Each "
        "tool call must be recorded as a CHECKPOINTED step (so that, in "
        "principle, a crash mid-loop resumes from the last completed tool call "
        "rather than restarting — use the framework's tracing / durable-step "
        "primitive for each tool call).\n"
        "Starting from `start`, apply the ops in `program` (a list of [op, arg], "
        "op in {add, mul}) in order, one checkpointed tool call each, and return "
        "the final accumulator.\n"
        "In Flyte v1 the only unit of recovery is a task = a pod, so a durable "
        "N-step loop is either one opaque uncheckpointed task or a pod-per-step "
        "explosion — the in-process checkpointed loop is not expressible. If "
        "your target cannot express it, record the trial as INFEASIBLE.\n"
        "Output contract — TRIAL_OUTPUT_JSON with:\n"
        "  answer : number  (accumulator after applying the whole program)"
    ),
    output_keys=["answer"],
    gen_inputs=_agent_inputs, expected=_agent_expected,
)


SPECS: dict[str, Spec] = {
    s.id: s for s in [
        ETL, FANOUT, CONDITIONAL, DYNAMIC_FANOUT, FIT_EVAL,       # group A
        OOM_RETRY, CIRCUIT_BREAKER, AGENT_LOOP,                   # group B
    ]
}


def make_inputs(spec_id: str, seed: int) -> dict:
    """Deterministic per-trial inputs for a spec."""
    return SPECS[spec_id].gen_inputs(random.Random(seed))


if __name__ == "__main__":
    # Self-test: every oracle must agree with itself on its own expected output.
    ok = True
    for sid, spec in SPECS.items():
        for seed in range(5):
            inp = make_inputs(sid, seed)
            want = spec.expected(inp)
            passed, why = spec.check(inp, want)
            if not passed:
                ok = False
                print(f"FAIL {sid} seed={seed}: {why}")
        example = json.dumps(spec.expected(make_inputs(sid, 0)))
        print(f"{spec.group} {sid:16s} {spec.difficulty:6s} "
              f"feasible_v1={spec.v1_feasible!s:5s} example_expected={example}")
    print("\nself-test:", "PASS" if ok else "FAIL")
