# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Write the randomized inputs for one trial to a JSON file.

    uv run make_inputs.py <spec_id> --seed 0 --out runs/v2/etl/trial0/inputs.json

Inputs are a deterministic function of (spec, seed), so a trial is reproducible
and a hardcoded answer cannot pass across seeds. `--show` prints instead of
writing.
"""
import argparse
import json
import os

from specs import SPECS, make_inputs


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec_id", help="one of: " + ", ".join(SPECS))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="inputs.json")
    ap.add_argument("--show", action="store_true", help="print, don't write")
    a = ap.parse_args()
    if a.spec_id not in SPECS:
        raise SystemExit(f"unknown spec {a.spec_id!r}; choose from {sorted(SPECS)}")
    inputs = make_inputs(a.spec_id, a.seed)
    blob = json.dumps(inputs, indent=2)
    if a.show:
        print(blob)
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        f.write(blob + "\n")
    print(f"wrote {a.out}: {json.dumps(inputs)}")


if __name__ == "__main__":
    main()
