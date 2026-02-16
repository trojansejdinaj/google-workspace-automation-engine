# Sheets Cleanup + Reporting Runbook

Purpose: how to run [workflows/sheets_cleanup_reporting](workflows/sheets_cleanup_reporting) and inspect outputs.

## 1) Prereqs

- Auth setup: see [docs/architecture/05-auth.md](docs/architecture/05-auth.md).
- Config files: start from [workflows/sheets_cleanup_reporting/config.example.yml](workflows/sheets_cleanup_reporting/config.example.yml) and copy to [workflows/sheets_cleanup_reporting/config.local.yml](workflows/sheets_cleanup_reporting/config.local.yml) for local secrets. Do not commit the local config file.

## 2) Run commands

```bash
./workflows/sheets_cleanup_reporting/demo.sh
# or
uv run gw run sheets_cleanup_reporting --config workflows/sheets_cleanup_reporting/config.example.yml
```

## 3) What gets written

- Runs dir: [runs/<run_id>/](runs/<run_id>/)
- Artifacts:
  - [runs/<run_id>/artifacts/report.csv](runs/<run_id>/artifacts/report.csv)
  - [runs/<run_id>/artifacts/needs_review.csv](runs/<run_id>/artifacts/needs_review.csv)
  - (optional) [runs/<run_id>/artifacts/cleanup_report.json](runs/<run_id>/artifacts/cleanup_report.json)
- Sheets tabs: report and needs_review (tab names come from the config).

## 4) Quick verification checklist

- Run directory exists under [runs/<run_id>/](runs/<run_id>/).
- Report file exists at [runs/<run_id>/artifacts/report.csv](runs/<run_id>/artifacts/report.csv) with metric/value rows.
- Needs-review file exists at [runs/<run_id>/artifacts/needs_review.csv](runs/<run_id>/artifacts/needs_review.csv) with row_number, reason, values_json.
- The report and needs_review tabs are updated in the target Sheet.

## 5) Troubleshooting

- Missing sheet tabs: the workflow creates report and needs_review tabs if they are missing; if the Sheets API call is blocked, you may need to create them manually.
- Stale rows: the workflow clears the report and needs_review tabs before writing; if you still see old rows, confirm the tab names match your config and the workflow has write access.
