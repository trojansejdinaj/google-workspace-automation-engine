# Engine execution contract

This is the single source of truth for how the engine executes workflows.

---

## What it is

**Location**: `src/gw_engine/engine.py`

The engine runs a **Workflow** (ordered steps) and enforces the step lifecycle, failure rules, and context persistence.

---

## Workflow vs Step

- **Workflow**: An ordered list of steps with a name. The engine controls the run boundary and overall failure policy.
- **Step**: A single unit of work with a `run(...) -> StepResult`. It runs at most once per workflow run.

---

## Step lifecycle + statuses (minimal)

Each step is in exactly one of these states:
- `PENDING` — not started yet
- `RUNNING` — currently executing
- `OK` — finished successfully
- `FAILED` — finished with failure

Lifecycle order:
- `PENDING` -> `RUNNING` -> (`OK` | `FAILED`)

The lifecycle is reflected in logs:
- `step_start` marks transition to `RUNNING`
- `step_end` marks `OK` or `FAILED`
- `step_error` records the failure details when `FAILED`

---

## StepResult contract (explicit failure)

Steps must return a `StepResult` (returning `None` is an error):
- `ok: bool` — `True` for success, `False` for failure
- `outputs: dict | None` — per-step outputs recorded by step name
- `error: str | None` — human-readable failure reason (required when `ok=False`)

A step **fails** if:
- It raises an exception, or
- It returns `StepResult(ok=False, ...)`

---

## Context model + persistence

Two objects are passed to every step:

- **RunContext** (immutable):
  - `run_id` — unique run identifier
  - `run_dir` — directory for run artifacts
  - `logs_path` — `runs/<run_id>/logs.jsonl`

- **RunState** (mutable):
  - `data` — shared workflow state (free-form)
  - `step_outputs` — outputs by step name

Persistence guarantees:
- The engine creates `runs/<run_id>/` at run start.
- The engine **persists RunState** to `runs/<run_id>/context.json` **after each step completes** and **again on failure**.
- Steps may write additional files under `run_dir`, but must not mutate `RunContext`.

---

## Failure semantics (strict)

On failure (exception or explicit failed result):
- The engine records `step_error` and `step_end` with status `FAILED`.
- The engine **stops immediately**. No further steps execute.
- The engine persists `context.json` after the failed step completes.

---

## Run artifacts on disk

During execution, the engine guarantees:
- `runs/<run_id>/` directory exists
- `runs/<run_id>/logs.jsonl` contains JSONL log events for run + steps
- `runs/<run_id>/context.json` contains the latest RunState

No other files are required by the engine contract.

---

## Usage example

```python
from pathlib import Path

from gw_engine.contracts import RunState, Step, StepResult, Workflow
from gw_engine.engine import run_workflow
from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext


def ok_step(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
    state.data["stage"] = "ok"
    return StepResult(ok=True, outputs={"stage": "ok"})


def fail_step(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
    return StepResult(ok=False, error="boom")


ctx = RunContext.create(Path("runs"))
log = JsonlLogger(path=ctx.logs_path, component="engine")
workflow = Workflow(name="demo", steps=[
    Step(name="ok_step", fn=ok_step),
    Step(name="fail_step", fn=fail_step),
])

run_workflow(workflow=workflow, ctx=ctx, log=log)
```
