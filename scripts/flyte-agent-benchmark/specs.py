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

Three groups:

  A — head-to-head. Expressible in BOTH Flyte v1 (flytekit) and v2 (flyte). These
      give the token / iteration comparison the benchmark is about.
  B — v2 capability. The value-dependent, in-process control-flow patterns v1
      cannot express even with @dynamic (OOM-catch-and-escalate, live-task
      racing, durable checkpointed loops). The v1 arm is expected to record
      `infeasible`; that is itself a result.
  C — applied ML, head-to-head. Realistic data + ML pipelines (record ETL with a
      join, model training, hyperparameter search, batch inference). Expressible
      in both arms, so they extend the head-to-head comparison — but heavier, and
      a solution may pull in numpy / pandas / scikit-learn.

Contract with a solution. The harness writes the trial's inputs to `inputs.json`.
The agent's `solution.py` runs its pipeline on those inputs and prints one line:

    TRIAL_OUTPUT_JSON:{...}      # the output dict named in the spec prompt

`oracle.py` reads that dict and calls `check()` below. Inputs are randomized per
trial (seeded), so a hardcoded answer fails — the only reliable way to pass is a
pipeline that actually computes the result.

Some specs keep part of the inputs *hidden* from the agent (`hidden_keys`, e.g.
held-out test labels): `make_inputs.py` strips those before writing the agent's
`inputs.json`, and the oracle regrades from the seed (so it still sees them). A
spec may also supply a custom `checker` for property-based grading (e.g. "test
accuracy >= 0.95") where exact-match is the wrong bar.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class Spec:
    id: str
    group: str                      # "A" head-to-head | "B" v2-only | "C" applied ML
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
    # Keys of the full inputs withheld from the agent (e.g. test labels). Stripped
    # by make_inputs.py; the oracle still sees them by regenerating from the seed.
    hidden_keys: list[str] = field(default_factory=list)
    # Optional property-based grader (inputs, produced) -> (ok, reason); overrides
    # the default exact/tolerance match when exact-match is the wrong bar.
    checker: Optional[Callable[[dict, dict], tuple[bool, str]]] = None

    def public(self, inputs: dict) -> dict:
        """The inputs the agent is allowed to see (hidden_keys removed)."""
        return {k: v for k, v in inputs.items() if k not in self.hidden_keys}

    def check(self, inputs: dict, produced: dict) -> tuple[bool, str]:
        """Grade a produced output dict against the ground truth."""
        if self.checker is not None:
            return self.checker(inputs, produced)
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


# --------------------------------------------------------------------------- #
# Group C — applied ML, head-to-head (realistic data + ML; both arms feasible)
# --------------------------------------------------------------------------- #

REGIONS = ["us-west", "us-east", "eu", "apac"]
STATUSES = ["completed", "completed", "cancelled", "pending"]   # ~half completed


def _etl_join_inputs(r: random.Random) -> dict:
    customers = [{"customer_id": cid, "region": r.choice(REGIONS)}
                 for cid in range(r.randint(6, 10))]
    orders = [{"order_id": oid,
               "customer_id": r.randint(0, len(customers) - 1),
               "amount_cents": r.randint(100, 10_000),
               "status": r.choice(STATUSES)}
              for oid in range(r.randint(15, 30))]
    return {"orders": orders, "customers": customers}


def _etl_join_expected(inp: dict) -> dict:
    region_of = {c["customer_id"]: c["region"] for c in inp["customers"]}
    agg: dict = {}
    for o in inp["orders"]:
        if o["status"] != "completed":
            continue
        reg = region_of.get(o["customer_id"])
        if reg is None:
            continue
        a = agg.setdefault(reg, [0, 0])
        a[0] += 1
        a[1] += o["amount_cents"]
    by_region = [{"region": reg, "orders": c, "total_cents": t}
                 for reg, (c, t) in sorted(agg.items())]
    return {"by_region": by_region}


ETL_JOIN = Spec(
    id="etl_join",
    group="C", difficulty="medium",
    title="Record ETL — filter, join, group-by",
    prompt=(
        "A realistic ETL over two tables:\n"
        "  `orders`   : list of records {order_id, customer_id, amount_cents, status}\n"
        "  `customers`: list of records {customer_id, region}\n"
        "Pipeline (use more than one step, passing the data between them):\n"
        "  1. Keep only orders with status == 'completed'.\n"
        "  2. Join each kept order to its customer's region on customer_id (drop "
        "orders whose customer_id has no matching customer).\n"
        "  3. Group by region: count orders and sum amount_cents per region.\n"
        "Return one row per region that has at least one completed order, SORTED "
        "ascending by region name.\n"
        "Output contract — TRIAL_OUTPUT_JSON with:\n"
        "  by_region : list of {region: str, orders: int, total_cents: int}"
    ),
    output_keys=["by_region"],
    gen_inputs=_etl_join_inputs, expected=_etl_join_expected,
)


def _blobs(r: random.Random, n: int) -> tuple[list, list]:
    # two well-separated 2-D Gaussian blobs -> a large margin, so any correct
    # classifier reaches ~100% and the grading threshold is unambiguous.
    xs, ys = [], []
    for _ in range(n):
        label = r.randint(0, 1)
        cx, cy = (3.0, 3.0) if label else (-3.0, -3.0)
        xs.append([round(cx + r.gauss(0, 0.6), 4), round(cy + r.gauss(0, 0.6), 4)])
        ys.append(label)
    return xs, ys


def _clf_inputs(r: random.Random) -> dict:
    x_train, y_train = _blobs(r, r.randint(40, 60))
    x_test, y_test = _blobs(r, 20)
    return {"X_train": x_train, "y_train": y_train, "X_test": x_test, "y_test": y_test}


def _clf_expected(inp: dict) -> dict:
    return {"predictions": inp["y_test"]}     # separable -> true labels are the target


def _clf_check(inp: dict, produced: dict) -> tuple[bool, str]:
    preds = produced.get("predictions")
    y_test = inp["y_test"]
    if not isinstance(preds, list):
        return False, "predictions must be a list"
    if len(preds) != len(y_test):
        return False, f"expected {len(y_test)} predictions, got {len(preds)}"
    try:
        ints = [int(p) for p in preds]
    except (TypeError, ValueError):
        return False, "predictions must be 0/1 ints"
    if len(set(ints)) < 2 and len(set(y_test)) > 1:
        return False, "degenerate predictions (all one class) — model not trained"
    acc = sum(int(p) == t for p, t in zip(ints, y_test)) / len(y_test)
    if acc < 0.95:
        return False, f"test accuracy {acc:.2f} < 0.95"
    return True, f"ok (accuracy={acc:.2f})"


TRAIN_CLF = Spec(
    id="train_classifier",
    group="C", difficulty="hard",
    title="Train a binary classifier, predict a held-out set",
    prompt=(
        "Train a binary classifier and predict a held-out test set.\n"
        "  `X_train`: list of [f1, f2] feature rows\n"
        "  `y_train`: list of 0/1 labels aligned to X_train\n"
        "  `X_test` : list of [f1, f2] rows to predict (NO labels are given)\n"
        "Fit any reasonable classifier on the training data, then predict a label "
        "for every row of X_test. The classes are well separated, so a correctly "
        "trained model should classify the test set essentially perfectly.\n"
        "Output contract — TRIAL_OUTPUT_JSON with:\n"
        "  predictions : list[int]  (0/1 per X_test row, in order)\n"
        "Graded on held-out test accuracy (must be >= 0.95), not exact match."
    ),
    output_keys=["predictions"],
    gen_inputs=_clf_inputs, expected=_clf_expected,
    hidden_keys=["y_test"], checker=_clf_check,
)


def _ridge_w(x: list, y: list, alpha: float) -> float:
    # single-feature ridge, no intercept: w = Sxy / (Sxx + alpha)
    sxx = sum(v * v for v in x)
    sxy = sum(x[i] * y[i] for i in range(len(x)))
    return sxy / (sxx + alpha)


def _val_mse(inp: dict, alpha: float) -> float:
    w = _ridge_w(inp["x_train"], inp["y_train"], alpha)
    xv, yv = inp["x_val"], inp["y_val"]
    return sum((yv[i] - w * xv[i]) ** 2 for i in range(len(xv))) / len(xv)


def _hpo_inputs(r: random.Random) -> dict:
    n = r.randint(12, 20)
    w_true = r.choice([-3.0, -2.0, 2.0, 3.0, 4.0])
    x_train = [round(r.uniform(-5, 5), 4) for _ in range(n)]
    y_train = [round(w_true * x + r.gauss(0, 1.5), 4) for x in x_train]
    x_val = [round(r.uniform(-5, 5), 4) for _ in range(8)]
    y_val = [round(w_true * x + r.gauss(0, 1.5), 4) for x in x_val]
    return {"x_train": x_train, "y_train": y_train, "x_val": x_val, "y_val": y_val,
            "alphas": [0.0, 0.1, 1.0, 10.0, 100.0]}


def _hpo_expected(inp: dict) -> dict:
    scores = {a: _val_mse(inp, a) for a in inp["alphas"]}
    best = min(scores, key=scores.get)
    return {"best_alpha": best, "val_mse": round(scores[best], 4)}


def _hpo_check(inp: dict, produced: dict) -> tuple[bool, str]:
    scores = {a: _val_mse(inp, a) for a in inp["alphas"]}
    best_mse = min(scores.values())
    pa, pm = produced.get("best_alpha"), produced.get("val_mse")
    try:
        match = [a for a in inp["alphas"] if abs(a - float(pa)) < 1e-6]
    except (TypeError, ValueError):
        return False, f"best_alpha not numeric: {pa!r}"
    if not match:
        return False, f"best_alpha {pa} is not one of {inp['alphas']}"
    if scores[match[0]] > best_mse + 1e-6:
        return False, f"alpha {pa} is not optimal (its val_mse {scores[match[0]]:.4f} > best {best_mse:.4f})"
    if pm is None or abs(float(pm) - round(scores[match[0]], 4)) > 1e-2:
        return False, f"val_mse {pm} != {round(scores[match[0]], 4)}"
    return True, f"ok (best_alpha={match[0]}, val_mse={round(best_mse,4)})"


HPO = Spec(
    id="hpo",
    group="C", difficulty="hard",
    title="Hyperparameter search — ridge regularization sweep",
    prompt=(
        "Run a hyperparameter search for a single-feature ridge regression "
        "(model y = w*x, no intercept; closed form w = Sxy / (Sxx + alpha), where "
        "Sxy = sum(x_i*y_i) and Sxx = sum(x_i^2) over the TRAIN split).\n"
        "  `x_train`,`y_train`: training pairs\n"
        "  `x_val`,`y_val`    : validation pairs\n"
        "  `alphas`           : candidate regularization strengths to try\n"
        "For EACH alpha, fit w on train and compute the validation mean squared "
        "error on (x_val, y_val); pick the alpha with the lowest validation MSE. "
        "Fit the candidates independently (a fan-out over alphas), then select the "
        "best.\n"
        "Output contract — TRIAL_OUTPUT_JSON with:\n"
        "  best_alpha : float  (the winning alpha)\n"
        "  val_mse    : float  (its validation MSE, rounded to 4 decimals)"
    ),
    output_keys=["best_alpha", "val_mse"],
    gen_inputs=_hpo_inputs, expected=_hpo_expected, checker=_hpo_check,
)


def _bi_inputs(r: random.Random) -> dict:
    w = [round(r.uniform(-1, 1), 4) for _ in range(3)]
    b = round(r.uniform(-1, 1), 4)
    n = r.randint(20, 40)
    features = [[round(r.uniform(-2, 2), 4) for _ in range(3)] for _ in range(n)]
    return {"weights": w, "bias": b, "features": features,
            "batch_size": r.choice([4, 5, 8])}


def _bi_expected(inp: dict) -> dict:
    preds = []
    for x in inp["features"]:
        z = sum(inp["weights"][j] * x[j] for j in range(len(x))) + inp["bias"]
        preds.append(1 if 1 / (1 + math.exp(-z)) > 0.5 else 0)
    return {"predictions": preds, "positives": sum(preds)}


BATCH_INFERENCE = Spec(
    id="batch_inference",
    group="C", difficulty="medium",
    title="Batched inference with a fixed model",
    prompt=(
        "Score many rows with a fixed pre-trained logistic model, in parallel "
        "batches.\n"
        "  `weights` : list of 3 floats\n  `bias`: float\n"
        "  `features`: list of [f1, f2, f3] rows to score\n"
        "  `batch_size`: how many rows each inference task should handle\n"
        "Split `features` into consecutive batches of size `batch_size` (the last "
        "may be smaller), run the batches in PARALLEL (one inference task per "
        "batch), and reassemble the predictions in the ORIGINAL row order. For a "
        "row, prediction = 1 if sigmoid(weights . row + bias) > 0.5 else 0, where "
        "sigmoid(z) = 1/(1+exp(-z)).\n"
        "Output contract — TRIAL_OUTPUT_JSON with:\n"
        "  predictions : list[int]  (0/1 per input row, in original order)\n"
        "  positives   : int        (count of 1s)"
    ),
    output_keys=["predictions", "positives"],
    gen_inputs=_bi_inputs, expected=_bi_expected,
)


SPECS: dict[str, Spec] = {
    s.id: s for s in [
        ETL, FANOUT, CONDITIONAL, DYNAMIC_FANOUT, FIT_EVAL,       # group A
        OOM_RETRY, CIRCUIT_BREAKER, AGENT_LOOP,                   # group B
        ETL_JOIN, TRAIN_CLF, HPO, BATCH_INFERENCE,                # group C
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
