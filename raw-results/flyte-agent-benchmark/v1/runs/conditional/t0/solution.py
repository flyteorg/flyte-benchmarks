# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["flytekit>=1.13"]
# ///
import json
import os
import uuid

from flytekit import conditional, task, workflow


@task
def cond_t0_times_two(x: int) -> int:
    return x * 2


@task
def cond_t0_plus_hundred(x: int) -> int:
    return x + 100


@workflow
def cond_t0_wf(value: int, threshold: int) -> int:
    return (
        conditional("pick")
        .if_(value >= threshold)
        .then(cond_t0_times_two(x=value))
        .else_()
        .then(cond_t0_plus_hundred(x=value))
    )


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "inputs.json")) as f:
        inputs = json.load(f)

    config_file = os.environ.get("FLYTE_AGENT_BENCH_CONFIG")

    if config_file:
        from flytekit.configuration import Config
        from flytekit.remote import FlyteRemote

        remote = FlyteRemote(
            Config.auto(config_file=config_file),
            default_project="flytesnacks",
            default_domain="development",
        )
        version = "t0" + uuid.uuid4().hex[:12]
        flyte_wf = remote.register_script(
            cond_t0_wf,
            source_path=here,
            module_name="solution",
            version=version,
        )
        ex = remote.execute(flyte_wf, inputs=inputs, wait=True)
        result = ex.outputs["o0"]
    else:
        result = cond_t0_wf(value=inputs["value"], threshold=inputs["threshold"])

    print("TRIAL_OUTPUT_JSON:" + json.dumps({"result": result}))
