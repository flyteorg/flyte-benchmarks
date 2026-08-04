# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["flytekit>=1.13"]
# ///
import json
import os

from flytekit import map_task, task, workflow


@task
def sq(x: int) -> int:
    return x * x


@workflow
def wf(xs: list[int]) -> list[int]:
    return map_task(sq)(x=xs)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    xs = inputs["xs"]

    config_file = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")

    if config_file:
        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote

        remote = FlyteRemote(
            Config.auto(config_file=config_file),
            default_project="flytesnacks",
            default_domain="development",
            interactive_mode_enabled=True,
        )
        import time

        version = f"fanout-map-t0-{int(time.time())}"
        ex = remote.execute(wf, inputs={"xs": xs}, version=version, wait=True)
        squares = ex.outputs["o0"]
    else:
        squares = wf(xs=xs)

    result = {"squares": list(squares)}
    print("TRIAL_OUTPUT_JSON:" + json.dumps(result))


if __name__ == "__main__":
    main()
