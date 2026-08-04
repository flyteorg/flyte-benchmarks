# Trial prompt template

The **identical** scaffold handed to the subagent under test, once per arm. The
orchestrator fills the four `{{...}}` slots and passes the whole thing as the
subagent prompt. Nothing about the scaffold differs between v1 and v2 except the
arm name, the cheatsheet, and the run/grade commands — that identity is what
keeps the two arms comparable. Do **not** paste any reference solution here.

---

You are authoring a data pipeline with **Flyte {{ARM}}** and nothing else. You
have one document to work from: the cheatsheet at `{{CHEATSHEET_PATH}}`. Read it
first. Do not fetch other docs or search the web — the equal-in-context-docs rule
is the point of this measurement.

Working directory: `{{WORKDIR}}` (already contains `inputs.json`). The oracle and
helpers are at `{{HARNESS_DIR}}`.

## The task

{{SPEC_PROMPT}}

## How to work

1. Read `{{CHEATSHEET_PATH}}` and `{{WORKDIR}}/inputs.json`.
2. Write `{{WORKDIR}}/solution.py`: a Flyte {{ARM}} pipeline that reads
   `inputs.json`, runs on those inputs, and prints exactly one line
   `TRIAL_OUTPUT_JSON:{...}` with the keys named in the task's output contract.
   (Run locally — no cluster needed — unless told otherwise.)
3. Run it, capturing the printed output:
   `cd {{WORKDIR}} && <run solution.py> | tee run.log`
4. Grade it:
   `uv run {{HARNESS_DIR}}/oracle.py {{SPEC_ID}} --inputs {{WORKDIR}}/inputs.json --produced run.log`
   - `ORACLE:PASS` → you are done. Stop immediately; do not polish.
   - `ORACLE:FAIL ...` or a crash → this counts as one failed iteration. Before
     fixing, classify the error:
     `uv run {{HARNESS_DIR}}/oracle.py --classify "<the error message>"`
     Note the `ERROR_CLASS:` (framework / logic / unknown) and the iteration
     number, then fix `solution.py` and go back to step 3.

## Rules

- **Turn budget: {{TURN_BUDGET}} run→fix iterations.** If you have not reached
  `ORACLE:PASS` by then, stop and report `success=false`.
- Never edit `inputs.json`, `oracle.py`, or the cheatsheet. Never hardcode the
  answer — inputs are randomized, so only a real pipeline passes.
- If the target framework **structurally cannot express** this task (the task
  says so, and the cheatsheet gives you no primitive for it), stop early and
  report `infeasible=true` with a one-line reason. Do not fake it.

## Finish

End your final message with one line, nothing after it:

`TRIAL_REPORT_JSON:{"success": <bool>, "infeasible": <bool>, "iterations": <int>, "errors": [{"iteration": <int>, "class": "framework|logic|unknown", "note": "<short>"}], "solution_path": "{{WORKDIR}}/solution.py"}`

- `iterations` = number of run→grade attempts you made (a first-try pass = 1).
- `errors` = one entry per failed attempt, with its classification.
