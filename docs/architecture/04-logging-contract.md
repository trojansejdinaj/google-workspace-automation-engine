# Logging contract (JSONL)

## Where logs live
Each run writes JSON Lines to:

- `runs/<run_id>/logs.jsonl`

One JSON object per line.

## Required fields (baseline)
Every log line MUST include:
- `ts` — UTC timestamp (e.g. `2026-01-29T15:28:00Z`)
- `level` — `DEBUG|INFO|ERROR`
- `component` — subsystem name (e.g. `engine`)
- `event` — machine-readable event name
- `run_id` — correlation id for the whole run

## Step lifecycle events
Every step MUST produce:
- `step_start`
  - `step`, `step_idx`, `start_ms`
- `step_end`
  - `step`, `step_idx`, `ok`, `duration_ms`, `end_ms`

On failure:
- `step_error`
  - `error_type`, `error_message` (+ optional stack later)

## Run lifecycle events
Each run MUST produce:
- `run_start`
- `run_end` (includes `duration_ms`)

## Notes
- Secrets must never be logged.
- Prefer stable keys over free-form messages.
