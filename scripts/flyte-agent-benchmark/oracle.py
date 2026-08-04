# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Grade one trial and classify authoring errors.

The agent's `solution.py` prints a line `TRIAL_OUTPUT_JSON:{...}`. Capture that
object (e.g. into `produced.json`) and run:

    uv run oracle.py <spec_id> --inputs inputs.json --produced produced.json

Exit 0 + "ORACLE:PASS" when the outputs match the ground truth for those exact
inputs; exit 1 + "ORACLE:FAIL <reason>" otherwise. The agent uses this as its
live oracle: write → run → grade → fix, until PASS.

`--classify` takes an error string on stdin/arg and prints whether the failure
is a *framework-mechanics* error (the ergonomic gap we're measuring) or a
*logic* error. Used when recording a failed iteration.
"""
import argparse
import json
import re
import sys

from specs import SPECS, make_inputs


# Substrings that mark a *framework-mechanics* failure — the agent fought the
# framework, not the problem. Split by arm because the tells differ.
FRAMEWORK_TELLS = [
    # v1 / flytekit
    "promise", "conditional", "with_overrides", "map_task", "@dynamic",
    "dynamic", "@eager", "not support", "does not support outputs", "compile",
    "launch plan", "launchplan", "flyteremote", "register", "pyflyte",
    "must be a keyword", "keyword arg", "cannot be used in a workflow",
    "expected an input of type", "type of the input", "flytekit",
    # v2 / flyte
    "taskenvironment", "env.task", "await", "coroutine", "was never awaited",
    ".aio", ".override", "init_from_config", "with_runcontext", "reusepolicy",
    "flyte.errors", "trace", "flyte.run", "resources", "image",
    # generic framework signals
    "no attribute", "importerror", "modulenotfound", "unexpected keyword",
    "missing required", "positional argument", "serialize", "not json",
]

LOGIC_TELLS = [
    "assert", "wrong", "mismatch", "got ", "want ", "expected ", "index",
    "zerodivision", "keyerror", "off by", "rounding", "order",
]


def classify(text: str) -> str:
    t = (text or "").lower()
    fw = sum(1 for s in FRAMEWORK_TELLS if s in t)
    lg = sum(1 for s in LOGIC_TELLS if s in t)
    if fw == 0 and lg == 0:
        return "unknown"
    return "framework" if fw >= lg else "logic"


def _extract_output(raw: str) -> dict:
    """Accept a bare JSON object or a line prefixed with TRIAL_OUTPUT_JSON:."""
    raw = raw.strip()
    if "TRIAL_OUTPUT_JSON:" in raw:
        raw = raw.split("TRIAL_OUTPUT_JSON:", 1)[1]
        raw = raw.splitlines()[0]
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("no JSON object found in produced output")
    return json.loads(m.group(0))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec_id", nargs="?", help="one of: " + ", ".join(SPECS))
    ap.add_argument("--inputs", help="inputs.json the trial ran on")
    ap.add_argument("--seed", type=int, help="alternatively, regenerate inputs from a seed")
    ap.add_argument("--produced", help="file with the TRIAL_OUTPUT_JSON (else read stdin)")
    ap.add_argument("--classify", help="classify an error string instead of grading")
    args = ap.parse_args()

    if args.classify is not None:
        print("ERROR_CLASS:" + classify(args.classify))
        return 0

    if not args.spec_id or args.spec_id not in SPECS:
        print(f"ORACLE:FAIL unknown spec {args.spec_id!r}; choose from {sorted(SPECS)}")
        return 2
    spec = SPECS[args.spec_id]

    if args.seed is not None:
        # Authoritative: regenerate the FULL inputs (incl. any withheld labels).
        inputs = make_inputs(args.spec_id, args.seed)
    elif args.inputs:
        inputs = json.load(open(args.inputs))
        missing = [k for k in spec.hidden_keys if k not in inputs]
        if missing:
            print(f"ORACLE:FAIL {spec.id} withholds {missing} from the agent's "
                  f"inputs.json — grade it with --seed <n>, not --inputs")
            return 2
    else:
        print("ORACLE:FAIL need --inputs or --seed")
        return 2

    raw = open(args.produced).read() if args.produced else sys.stdin.read()
    try:
        produced = _extract_output(raw)
    except Exception as e:
        print(f"ORACLE:FAIL could not parse produced output: {e}")
        return 1

    ok, why = spec.check(inputs, produced)
    if ok:
        print("ORACLE:PASS")
        return 0
    print(f"ORACLE:FAIL {why}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
