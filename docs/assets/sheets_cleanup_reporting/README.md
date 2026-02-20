# sheets_cleanup_reporting sample assets

This folder contains sanitized sample outputs for portfolio/demo documentation.

## Files
- `sample_audit.json`
  - Run + step audit bundle exported by `gw export <run_id> --format json`.
  - Sanitized: `run_id` is replaced with `SAMPLE_RUN_ID`.
- `sample_audit.csv`
  - Flat step-level audit export from `gw export <run_id> --format csv`.
  - Sanitized: `run_id` is replaced with `SAMPLE_RUN_ID`.
- `sample_report.csv`
  - Report metrics CSV produced by workflow artifacts (`runs/<run_id>/artifacts/report.csv`).
  - Sanitized: `run_id` is replaced with `SAMPLE_RUN_ID`.
- `sample_needs_review.csv`
  - Needs-review rows with reasons from workflow artifacts (`runs/<run_id>/artifacts/needs_review.csv`).
  - Sample content only; no secrets or real sheet IDs.
- `portfolio-01.png`
  - Placeholder image for terminal end-banner screenshot.
- `portfolio-02.png`
  - Placeholder image for post-run Google Sheet tabs screenshot.

## Portfolio screenshots (required)
These `.png` files are placeholders and are intentionally empty until captured.

1) `portfolio-01.png`
   - Capture terminal output after `bash ./demo.sh` finishes.
   - Include end banner lines showing: `run_id`, `status`, `audit_json`, `audit_csv`.

2) `portfolio-02.png`
   - Capture Google Sheet UI after run.
   - Show `report` and `needs_review` tabs updated.

## Reproduce with demo.sh
From repo root:

```bash
cd workflows/sheets_cleanup_reporting
bash ./demo.sh
```

After completion, note the `run_id` from the end banner and collect files from:
- `runs/<run_id>/audit.json`
- `runs/<run_id>/audit.csv`
- `runs/<run_id>/artifacts/report.csv`
- `runs/<run_id>/artifacts/needs_review.csv`

## Sanitization rules
- Do not include real spreadsheet IDs, tokens, or credentials.
- Redact run identifiers in portfolio samples (use `SAMPLE_RUN_ID`).
- Redact emails if present.
