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
3) writes a cleaned tab + a report tab
4) saves per-run artifacts under `runs/<run_id>/artifacts/`

## Demo (local)
1) Copy the example config:
   - `workflows/sheets_cleanup_reporting/config.example.yml`

2) Run:
   - `./workflows/sheets_cleanup_reporting/demo.sh`

Or directly:
- `uv run gw run sheets_cleanup_reporting --config workflows/sheets_cleanup_reporting/config.example.yml`

## Outputs
### Sheets
- Cleaned tab: `tabs.cleaned_tab`
- Report tab: `tabs.report_tab`

### Run artifacts (per run)
- `runs/<run_id>/logs.jsonl`
- `runs/<run_id>/summary.json`
- `runs/<run_id>/artifacts/report.json`
- optional: `runs/<run_id>/artifacts/cleaned_preview.csv`
