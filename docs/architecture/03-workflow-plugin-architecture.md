# Workflow plugin architecture

Workflows are plugins that define a sequence of steps executed by the engine.
The engine core stays generic; workflow code holds the Google Workspace specifics.

---

## Core interfaces (actual)

Defined in `src/gw_engine/contracts.py`:

- **Workflow**
  - `name: str`
  - `steps: list[Step]`

- **Step**
  - `name: str`
  - `fn(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult`

- **StepResult**
  - `ok: bool`
  - `outputs: dict | None` (captured into run context + step summaries)
  - `error: str | None` (required when ok=False)

---

## Plugin locations

### 1) Built-in engine plugins (preferred)
Location:
- `src/gw_engine/workflows/<workflow>.py`

These are registered in:
- `src/gw_engine/workflows/__init__.py`

The CLI will prefer these for `gw run <workflow> ...`.

### 2) Repo-local workflows (back-compat / dev)
Location:
- `workflows/<workflow>/workflow.py`

Required function:
- `get_workflow(cfg) -> Workflow`

Loaded by:
- `src/gw_engine/workflow_loader.py`

---

## Artifact indexing (T5)

Workflows can write artifacts under:
- `runs/<run_id>/artifacts/`

To keep outputs discoverable, workflows should register outputs in:
- `runs/<run_id>/artifacts/index.json`

Registration helper:
- `gw_engine.artifacts.register_artifact(...)`

---

## Execution + logging

Workflows are executed by the engine runtime (`gw_engine.engine`), which is responsible for:

- emitting `run_start` / `run_end`
- emitting `step_start` / `step_end` (with status + duration)
- propagating `run_id` into all logs for correlation

Workflow code should focus on:
- validating config
- calling Workspace APIs / transforms
- writing outputs + registering artifacts

## Gmail intake adapter boundary

- Responsibilities: search/fetch Gmail messages, decode bodies, and support fixture generation for parser tests.
- Boundary: workflow step calls `GmailAdapter`; `GmailAdapter` uses the client factory service (`gw_engine.clients`).
- Workflow remains orchestration-only: config, metrics, outputs, and artifact registration.
