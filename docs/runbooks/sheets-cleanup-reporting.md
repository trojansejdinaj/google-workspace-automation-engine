# Sheets Cleanup + Reporting Runbook

Purpose: how to run [sheets_cleanup_reporting](../../workflows/sheets_cleanup_reporting/README.md) and inspect outputs.

## 1) Prereqs

- Auth setup: see [Google auth](../architecture/05-auth.md).
- Config files: start from [config.example.yml](../../workflows/sheets_cleanup_reporting/config.example.yml) and copy to `workflows/sheets_cleanup_reporting/config.local.yml` for local values. Do not commit the local config file.

## 2) Run commands

```bash
./workflows/sheets_cleanup_reporting/demo.sh
# or
uv run gw run sheets_cleanup_reporting --config workflows/sheets_cleanup_reporting/config.example.yml
```

## 3) What gets written

- Runs dir: `runs/<run_id>/`
- Artifacts:
  - `runs/<run_id>/artifacts/report.csv`
  - `runs/<run_id>/artifacts/needs_review.csv`
  - optional `runs/<run_id>/artifacts/cleanup_report.json`
- Sheets tabs: report and needs_review (tab names come from the config).

## 4) Quick verification checklist

- Run directory exists under `runs/<run_id>/`.
- Report file exists at `runs/<run_id>/artifacts/report.csv` with metric/value rows.
- Needs-review file exists at `runs/<run_id>/artifacts/needs_review.csv` with row_number, reason, values_json.
- The report and needs_review tabs are updated in the target Sheet.

## 5) Troubleshooting

- Missing sheet tabs: the workflow creates report and needs_review tabs if they are missing; if the Sheets API call is blocked, you may need to create them manually.
- Stale rows: the workflow clears the report and needs_review tabs before writing; if you still see old rows, confirm the tab names match your config and the workflow has write access.

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
