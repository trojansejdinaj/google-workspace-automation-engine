# Engine execution contract

This is the single source of truth for how the engine executes workflows.

---

## What it is

**Location**: `src/gw_engine/engine.py`

The engine runs a **Workflow** (ordered steps) and enforces:

- Step lifecycle + status transitions
- Failure rules (stop-on-failure)
- Context persistence
- Run + step summaries (for audit/export)

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
- `step_error` records failure details when `FAILED`

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
- The engine finalizes run/step summaries with failure details.

---

## Run artifacts on disk (engine guarantees)

During execution, the engine guarantees:

- `runs/<run_id>/` directory exists
- `runs/<run_id>/logs.jsonl` contains JSONL log events for run + steps
- `runs/<run_id>/context.json` contains the latest RunState
- `runs/<run_id>/run.json` contains run-level summary (status + timestamps + duration)
- `runs/<run_id>/steps.json` contains per-step summaries (status + timestamps + duration)
- Optionally `runs/<run_id>/audit.json` can be written as a convenience bundle `{ run, steps }`

No other files are required by the engine contract.

### Minimum run summary fields (`run.json`)

- `run_id`
- `workflow_name`
- `status` (`OK` | `FAILED`)
- `started_at`
- `finished_at` (or `ended_at`)
- `duration_ms`
- `config_hash` (optional)
- `git_sha` (optional)
- `error_summary` (optional)

### Minimum step summary fields (`steps.json`)
Per step:

- `step_index`
- `step_name`
- `status` (`OK` | `FAILED`)
- `started_at`
- `finished_at`
- `duration_ms`
- `error_code` (optional)
- `error_message` (optional)
- `metrics` (optional JSON)

---

## Audit export contract (CLI)

Audit exports are generated after-the-fact from persisted summaries:

- `gw export <run_id> --format json`
  - Writes `runs/<run_id>/audit.json` by default
  - Output is a bundle `{ run: <run.json>, steps: <steps.json> }`

- `gw export <run_id> --format csv`
  - Writes `runs/<run_id>/audit.csv` by default
  - CSV is **one row per step**, with run-level fields repeated per row

CSV minimum columns (stable order):
```
run_id
workflow_name
run_status
run_started_at
run_finished_at
run_duration_ms
step_index
step_name
step_status
step_started_at
step_finished_at
step_duration_ms
step_error_code
step_error_message
step_metrics_json
```

Export error behavior:

- If `runs/<run_id>/` does not exist, the command must fail with a clear message and non-zero exit code.
- If required summary files are missing/corrupt, the command must fail clearly (do not silently produce partial exports).

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
workflow = Workflow(
    name="demo",
    steps=[
        Step(name="ok_step", fn=ok_step),
        Step(name="fail_step", fn=fail_step),
    ],
)

run_workflow(workflow=workflow, ctx=ctx, log=log)

---

## Artifacts index (T5)

In addition to the engine-guaranteed files, workflows may emit artifacts.
To make artifacts discoverable, each run has an **artifact index**:

- `runs/<run_id>/artifacts/index.json`

### Index format (stable)

Append-only: workflows may register multiple artifacts over time; the index grows as artifacts are produced.

The file is a JSON array of records:

- `name` (string) — stable key (e.g. `report_csv`)
- `type` (string) — `csv` | `json` | `txt` | etc.
- `path` (string) — path relative to `runs/<run_id>/` (posix)
- `created_at` (string) — ISO UTC timestamp
- `metadata` (object) — free-form metrics (row counts, schema cols, etc.)

Workflows register artifacts via `gw_engine.artifacts.register_artifact(...)`.

---

## API retries + error handling

### Retryable errors

Google API client requests automatically retry on transient errors:

- **429** (Too Many Requests)
- **500, 502, 503, 504** (Server errors)
- **403** with reason `rateLimitExceeded` or `userRateLimitExceeded`

### Backoff strategy

- Exponential backoff with jitter
- Default: `max_retries=5`, `initial_backoff_s=0.5`, `max_backoff_s=8.0`, `jitter_ratio=0.2`
- Configurable via `ClientSettings(retry=RetryPolicy(...))`

### Retry exhaustion

When retries are exhausted, raises `APIRetryExhausted` exception with:

- `operation` — API operation that failed (e.g. `sheets.spreadsheets.values.get`)
- `attempts` — total attempts made (initial + retries)
- `status_code` — HTTP status code
- `reason` — rate limit reason (403 errors only)
- `message` — error description

### Step failure handling

When a step raises an exception (including `APIRetryExhausted`):

1. Step status marked `FAILED`
2. Error artifact written to `runs/<run_id>/errors/<workflow>__<step>.json`
3. `step_failed` event logged with error details + artifact path
4. Run finalization proceeds (run.json, steps.json written)
5. Execution stops (subsequent steps not run)

### Error artifact format

```json
{
  "run_id": "...",
  "workflow": "...",
  "step": "...",
  "status": "FAILED",
  "error_type": "APIRetryExhausted",
  "error_message": "...",
  "operation": "sheets.spreadsheets.values.get",
  "status_code": 429,
  "attempts": 5,
  "reason": "rateLimitExceeded",
  "ts": "2026-02-19T10:30:00Z"
}
```

Non-API exceptions omit `operation`, `status_code`, `attempts`, `reason`.

---

## Rerun safety (idempotency)

### Sheets write strategy

Workflows writing to Sheets MUST use **clear-then-write** pattern:

1. Clear target tab/range completely
2. Write new data from A1

**Never append** without deduplication/upsert logic.

### Artifact naming

Local artifacts use deterministic names:

- Fixed filenames within run directory: `report.csv`, `cleanup.json`
- Each run gets unique directory: `runs/<run_id>/artifacts/`
- Reruns with same `run_id` overwrite files deterministically
- Different runs create separate directories

### Expectations

- Running a workflow twice back-to-back MUST NOT duplicate rows in Sheets
- Report tabs MUST be completely replaced on each run
- Artifacts MUST overwrite (not append) within same run_id
