# sheets_cleanup_reporting

## Problem
Google Sheets tabs that act like “living data” drift over time:
- inconsistent dates/amount formats
- empty rows
- duplicate entries
- missing required fields
- no visibility into what got fixed vs dropped

## Solution
This workflow:
1) loads rows from an input tab
2) cleans + validates deterministically (idempotent)
3) produces a cleaned preview + validation annotations
4) writes per-run artifacts under `runs/<run_id>/artifacts/`

## Demo (local)
1) Copy the example config:
   - `workflows/sheets_cleanup_reporting/config.example.yml`

2) Run:
   - `./workflows/sheets_cleanup_reporting/demo.sh`

Or directly:
- `uv run gw run sheets_cleanup_reporting --config workflows/sheets_cleanup_reporting/config.example.yml`

## Schema & Validation (T2)
- Schema lives in `config.yml` under `rules.schema`.
- Invalid rows are preserved and annotated with reasons, not dropped.
- Transform failures (T3) are recorded separately from schema validation failures.
- Both are included in the cleanup report examples and count toward invalid_count.
- Validation output: `runs/<run_id>/artifacts/validation_report.json`.
- Run locally: `./workflows/sheets_cleanup_reporting/demo.sh` and `make test`.

## T3 — Cleanup transforms + dedupe + metrics
This workflow applies cleanup transforms before strict schema validation:

Order:
1) Apply transforms (strings/dates/numbers)
2) Validate against `rules.schema`
3) Dedupe validated rows using `dedupe.keys` (keys computed on normalized values).
4) Emit metrics: rows_in, rows_out, invalid_count

### Config
- `transforms.strings`: trim/collapse_spaces + per-field case
- `transforms.dates.formats`: accepted input formats, normalized to YYYY-MM-DD
- `transforms.numbers.strip_commas`: tolerate "1,234.50"
- `dedupe.keys`: uniqueness keys (post-transform)
- `dedupe.keep`: first|last

### Output artifact
`runs/<run_id>/artifacts/cleanup_report.json` includes:
- counts (rows_in / invalid_count / rows_out / dedupe_removed)
- examples of transform-invalid + validation-invalid rows
- cleaned preview

## Outputs
- Sheets tabs updated: report + needs_review (names come from config).
- Run artifacts: `runs/<run_id>/artifacts/report.csv` and `runs/<run_id>/artifacts/needs_review.csv` (optional `runs/<run_id>/artifacts/cleanup_report.json`).

### Screenshots
- [Report tab](docs/assets/sheets_cleanup_reporting/report-tab.png)
- [Needs-review tab](docs/assets/sheets_cleanup_reporting/needs-review-tab.png)

### Evidence (DoD proof)
Save a proof file:
`runs/_evidence/01.04.02.P02.T3-proof.txt`

Include:
1) Config dump (transforms + dedupe)
2) 5–10 log lines (rows_in, invalid_count, dedupe_removed, rows_out)
3) Output snippet (first 5–10 cleaned rows from cleanup_report.json)
