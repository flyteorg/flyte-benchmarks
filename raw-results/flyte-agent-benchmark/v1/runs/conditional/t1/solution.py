# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["flytekit>=1.13"]
# ///
import hashlib
import json
import os

from flytekit import conditional, task, workflow


@task
def times_two(x: int) -> int:
    return x * 2


@task
def plus_hundred(x: int) -> int:
    return x + 100


@workflow
def wf(value: int, threshold: int) -> int:
    return (
        conditional("pick")
        .if_(value >= threshold)
        .then(times_two(x=value))
        .else_()
        .then(plus_hundred(x=value))
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
        # Give this workflow a content-unique version so it can't collide with
        # a same-named `wf` registered under a different spec/signature on
        # this shared project/domain.
        version = "conditional-t1-" + hashlib.sha1(
            open(os.path.abspath(__file__), "rb").read()
        ).hexdigest()[:16]

        # register_script fast-packages this local file so the remote pod can
        # actually import it (plain remote.execute() assumes the code is
        # already baked into the image, which it isn't here).
        flyte_wf = remote.register_script(
            wf,
            version=version,
            source_path=here,
            module_name="solution",
        )

        ex = remote.execute(
            flyte_wf,
            inputs=inputs,
            wait=True,
        )
        result = ex.outputs["o0"]
    else:
        result = wf(value=inputs["value"], threshold=inputs["threshold"])

    print(f"TRIAL_OUTPUT_JSON:{json.dumps({'result': result})}")
