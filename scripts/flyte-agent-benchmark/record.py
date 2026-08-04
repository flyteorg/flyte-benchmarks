# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Append one trial result as a JSON line.

One line per (arm x spec x trial). The schema is deliberately small and flat so
the same file feeds `score.py` and the repo's plotting conventions.

    uv run record.py --arm v2 --spec conditional --seed 0 \
        --tokens 8123 --iterations 2 --success \
        --out agent_results.jsonl

Fields:
  arm         "v1" | "v2"                the framework under test
  spec        spec id                    (see specs.py)
  group       "A" | "B"                  filled in from the spec
  difficulty  easy|medium|hard           filled in from the spec
  seed        int                        selects the trial's randomized inputs
  trial       int                        repeat index for that (arm, spec)
  tokens      int|null   HEADLINE — harness-measured tokens to green (the
                         subagent's reported `subagent_tokens`). null in manual
                         mode where no per-trajectory token meter exists.
  output_tokens int|null  proxy: count_tokens.py over the final solution.py
  iterations  int         run -> fix cycles until the first green run (>=1)
  success     bool        oracle PASSed within the turn budget
  infeasible  bool        arm structurally cannot express the spec (group B on v1)
  errors      list[{iteration:int, class:"framework"|"logic"|"unknown", note}]
  model       str|null    the model driving the agent (for the record)
  wall_seconds number|null
  ts          iso8601
"""
import argparse
import json
import time

from specs import SPECS


def build_row(arm, spec_id, *, seed=0, trial=0, tokens=None, output_tokens=None,
              iterations=1, success=False, infeasible=False, errors=None,
              model=None, wall_seconds=None):
    if spec_id not in SPECS:
        raise SystemExit(f"unknown spec {spec_id!r}; choose from {sorted(SPECS)}")
    if arm not in ("v1", "v2"):
        raise SystemExit("--arm must be v1 or v2")
    s = SPECS[spec_id]
    return {
        "arm": arm, "spec": spec_id, "group": s.group, "difficulty": s.difficulty,
        "seed": seed, "trial": trial,
        "tokens": tokens, "output_tokens": output_tokens,
        "iterations": iterations, "success": bool(success),
        "infeasible": bool(infeasible), "errors": errors or [],
        "model": model, "wall_seconds": wall_seconds,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--trial", type=int, default=0)
    ap.add_argument("--tokens", type=int)
    ap.add_argument("--output-tokens", type=int, dest="output_tokens")
    ap.add_argument("--iterations", type=int, default=1)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--success", action="store_true")
    g.add_argument("--fail", action="store_true")
    ap.add_argument("--infeasible", action="store_true")
    ap.add_argument("--errors", help="JSON list of error records", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--wall-seconds", type=float, dest="wall_seconds")
    ap.add_argument("--out", default="agent_results.jsonl")
    a = ap.parse_args()

    errors = json.loads(a.errors) if a.errors else None
    row = build_row(a.arm, a.spec, seed=a.seed, trial=a.trial, tokens=a.tokens,
                    output_tokens=a.output_tokens, iterations=a.iterations,
                    success=a.success and not a.fail, infeasible=a.infeasible,
                    errors=errors, model=a.model, wall_seconds=a.wall_seconds)
    with open(a.out, "a") as f:
        f.write(json.dumps(row) + "\n")
    print("RECORDED:" + json.dumps(row))


if __name__ == "__main__":
    main()
