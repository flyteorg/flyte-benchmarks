# /// script
# requires-python = ">=3.12"
# dependencies = ["flytekit>=1.13"]
# ///
"""Reference solution (HELD OUT). Spec `fanout_map`, Flyte v1 — map_task."""
import json

from flytekit import map_task, task, workflow


@task
def sq(x: int) -> int:
    return x * x


@workflow
def wf(xs: list[int]) -> list[int]:
    return map_task(sq)(x=xs)


if __name__ == "__main__":
    inp = json.load(open("inputs.json"))
    squares = wf(**inp)                       # single output -> bare list
    print("TRIAL_OUTPUT_JSON:" + json.dumps({"squares": list(squares)}))
