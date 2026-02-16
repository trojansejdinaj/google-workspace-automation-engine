# Evidence folder (tracked)

This folder exists so Git tracks `runs/_evidence/` and we have a stable place for **curated proof** of completed tasks.

## What to put here
Small, intentional artifacts that prove a task is done, for example:
- `t1-quality-gates.txt` — terminal output showing `make check` passed (ruff/mypy/pytest green)
- `t2-cli-help.txt` — `uv run gw --help` output proving the CLI entry works
- `t3-demo-summary.txt` — final summary block (run_id, status, duration, steps ok/failed)

Screenshots are fine too:
- `t1-quality-gates.png`

## What NOT to put here
Do not commit per-run artifacts:
- `runs/<run_id>/...` logs and outputs
- large exports/dumps
- anything that changes every run

Those belong in `runs/` (ignored by git).

## Naming convention
Use task-coded filenames:
- `01.04.02.P01.T1-quality-gates.txt`
- `01.04.02.P01.T1-quality-gates.png`

## KPI naming (for proof files)
Use a single canonical set for evidence proofs:
- `rows_in`
- `rows_valid`
- `rows_invalid`
- `dedupe_removed`
- `rows_out`

If code logs `invalid_count`, map it to `rows_invalid` in the proof for consistency (or update code to log `rows_invalid` too).

## Proof template
Copy/paste skeleton:

```
RESULT: ...
CONFIG DUMP:
<...>
LOG LINES (5-10):
<...>
OUTPUT SNIPPET:
<...>
```
