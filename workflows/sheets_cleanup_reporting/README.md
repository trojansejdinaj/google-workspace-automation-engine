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

## 2-minute live run

```bash
cd workflows/sheets_cleanup_reporting
cp -n config.example.yml config.local.yml
```

Edit `config.local.yml` (local only):
- Set `sheets.sheet_id` from your Sheet URL: `https://docs.google.com/spreadsheets/d/<id>/edit`
- Keep real IDs redacted in evidence/proof files.

Run:

```bash
bash ./demo.sh
```

Expected outputs:
- `runs/<run_id>/audit.json`
- `runs/<run_id>/audit.csv`
- `runs/<run_id>/logs.jsonl`
- `runs/<run_id>/errors/`

Rerun behavior:
- Each run creates a new `run_id` directory under `runs/`.
- Existing prior runs are not overwritten.

### Troubleshooting
- Auth: ensure `GW_SA_TEST_SHEET_ID` and Google auth env vars are set for your local setup.
- Permissions: sheet must be shared with the credential identity used by the workflow.
- Tab mismatch: verify `tabs.input_tab`, `tabs.cleaned_tab`, `tabs.report_tab`, `tabs.needs_review_tab` exist or are creatable.

### Portfolio screenshots
Capture these exactly:
1) `docs/assets/sheets_cleanup_reporting/portfolio-01.png`
	- Terminal output showing `bash ./demo.sh` end banner with `run_id`, `status`, `audit_json`, `audit_csv`.
2) `docs/assets/sheets_cleanup_reporting/portfolio-02.png`
	- Google Sheet UI after run showing `report` and `needs_review` tabs updated.

Placeholders are checked in under `docs/assets/sheets_cleanup_reporting/` and should be replaced with actual screenshots.

## Schema & Validation
- Schema lives in `config.yml` under `rules.schema`.
- Invalid rows are preserved and annotated with reasons, not dropped.
- Transform failures (T3) are recorded separately from schema validation failures.
- Both are included in the cleanup report examples and count toward invalid_count.
- Validation output: `runs/<run_id>/artifacts/validation_report.json`.
- Run locally: `./workflows/sheets_cleanup_reporting/demo.sh` and `make test`.

## Cleanup transforms + dedupe + metrics
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
Portfolio assets are tracked under `docs/assets/sheets_cleanup_reporting/`.

### Historical evidence (DoD proof)
Save a proof file:
`runs/_evidence/01.04.02.P02.T3-proof.txt`

Include:
1) Config dump (transforms + dedupe)
2) 5–10 log lines (rows_in, invalid_count, dedupe_removed, rows_out)
3) Output snippet (first 5–10 cleaned rows from cleanup_report.json)

<!-- 06.03.01.P01.T02:portfolio-proof:start -->
## Portfolio proof — Sheets cleanup + reporting workflow

This workflow demonstrates a Google Sheets cleanup/reporting automation that can be shown as portfolio evidence.

### Demo command

    bash workflows/sheets_cleanup_reporting/demo.sh

### Proven run

- workflow: `sheets_cleanup_reporting`
- run_id: `fc494290d5ae48a69554e741d9ef530b`
- status: `SUCCESS`
- run_dir: `runs/fc494290d5ae48a69554e741d9ef530b`

### Expected run artifacts

The successful demo produces:

- `runs/fc494290d5ae48a69554e741d9ef530b/audit.json`
- `runs/fc494290d5ae48a69554e741d9ef530b/audit.csv`
- `runs/fc494290d5ae48a69554e741d9ef530b/logs.jsonl`
- `runs/fc494290d5ae48a69554e741d9ef530b/errors/`
- `runs/fc494290d5ae48a69554e741d9ef530b/artifacts/report.csv`
- `runs/fc494290d5ae48a69554e741d9ef530b/artifacts/needs_review.csv`
- `runs/fc494290d5ae48a69554e741d9ef530b/artifacts/cleanup_report.json`
- `runs/fc494290d5ae48a69554e741d9ef530b/artifacts/index.json`

### Validated cleanup results

- rows_in: `5`
- rows_valid_pre_dedupe: `3`
- invalid_count: `3`
- dedupe_removed: `1`
- rows_out: `2`
- invalid_rate: `0.6000`
- needs_review rows: `3`
- audit status: `OK`
- audit steps: `validate_config=OK`, `run_cleanup=OK`

### Screenshot evidence

Portfolio screenshots are saved at:

- `runs/_evidence/06.03.01.P01.T02/screenshots/01-terminal-success-banner.png`
- `runs/_evidence/06.03.01.P01.T02/screenshots/02-report-tab.png`
- `runs/_evidence/06.03.01.P01.T02/screenshots/03-needs-review-tab.png`
- `runs/_evidence/06.03.01.P01.T02/screenshots/04-artifact-view.png`

### Business explanation

The workflow turns messy spreadsheet input into operator-ready outputs. It reads raw rows, validates required fields and data types, separates rows that need manual review, removes duplicates, writes clean output rows, and generates a report that explains the cleanup funnel.

This is useful for small businesses or operations teams that depend on spreadsheets but need repeatable cleanup, auditability, and clear exception handling before using the data for reporting, CRM updates, billing, finance review, or downstream automation.

### Evidence files

- `runs/_evidence/06.03.01.P01.T02/block-01-sheets-workflow-demo-setup.md`
- `runs/_evidence/06.03.01.P01.T02/block-02-run-sheets-cleanup-workflow.md`
- `runs/_evidence/06.03.01.P01.T02/block-03-validate-sheets-outputs.md`
- `runs/_evidence/06.03.01.P01.T02/block-04-capture-sheets-screenshots.md`
- `runs/_evidence/06.03.01.P01.T02/proof.md`
<!-- 06.03.01.P01.T02:portfolio-proof:end -->
