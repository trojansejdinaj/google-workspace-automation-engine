# 06.03.01.P01.T02 — Block 01 — Sheets Workflow Demo Setup

## Block
Sheets Workflow Demo Setup

## Scope
Opened the Sheets cleanup/reporting workflow docs, config, runbook, and demo command.
Confirmed expected config, expected outputs, and first-run status.

## Inspected files
- workflows/sheets_cleanup_reporting/README.md
- workflows/sheets_cleanup_reporting/config.example.yml
- workflows/sheets_cleanup_reporting/demo.sh
- docs/runbooks/sheets-cleanup-reporting.md

## Expected run command
bash workflows/sheets_cleanup_reporting/demo.sh

## Expected outputs
- runs/<run_id>/audit.json
- runs/<run_id>/audit.csv
- runs/<run_id>/logs.jsonl
- runs/<run_id>/errors/
- runs/<run_id>/artifacts/report.csv
- runs/<run_id>/artifacts/needs_review.csv
- runs/<run_id>/artifacts/cleanup_report.json

## Local config
- workflows/sheets_cleanup_reporting/config.local.yml was created locally.
- Real spreadsheet IDs and credentials are not committed.
- sheet_id is resolved through GW_SA_TEST_SHEET_ID or local config.

## First run result
The first demo setup run completed successfully.

- workflow: sheets_cleanup_reporting
- run_id: 4309037c95114e8894313b5db977b636
- status: SUCCESS
- ok: True
- command_exit_code: 0
- run_dir: runs/4309037c95114e8894313b5db977b636
- duration_ms: 3880
- audit_json: runs/4309037c95114e8894313b5db977b636/audit.json
- audit_csv: runs/4309037c95114e8894313b5db977b636/audit.csv
- logs: runs/4309037c95114e8894313b5db977b636/logs.jsonl
- errors_dir: runs/4309037c95114e8894313b5db977b636/errors

## Notes / blockers
- Service account auth passed before the demo run.
- The workflow starts and completes successfully.
- Block 01 proves the setup, config path, run command, and first successful run directory.
- Full artifact validation is reserved for Block 02 and Block 03.
