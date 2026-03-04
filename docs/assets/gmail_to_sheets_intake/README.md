# gmail_to_sheets_intake sample assets

This folder contains sanitized sample assets for portfolio/demo documentation.

## Files
- `portfolio-01.png`
	- Placeholder image for triage sheet screenshot after a run.
	- Show columns/values including: `message_id`, parsed fields, `gmail_link`, `status`.
- `portfolio-02.png`
	- Placeholder image for artifact screenshot.
	- Show `runs/<run_id>/artifacts/triage_export.csv` in folder view or opened as a snippet.

## Portfolio screenshots (required)
These `.png` files are placeholders and are intentionally empty until captured.

1) `portfolio-01.png`
	 - Capture the Google Sheet `triage` tab after a run.
	 - Include rows keyed by `message_id` and visible `gmail_link` + `status` columns.

2) `portfolio-02.png`
	 - Capture artifacts for the same run.
	 - Show `artifacts/triage_export.csv` in the run folder or open and show a short snippet.

## Reproduce with demo.sh
From repo root:

```bash
cd workflows/gmail_to_sheets_intake
bash ./demo.sh
```

After completion, note `run_id` from terminal output and collect evidence from:
- `runs/<run_id>/artifacts/triage_export.csv`
- `runs/_evidence/01.04.02.P03.T4-check-proof.txt`

## Sanitization rules
- Do not include real spreadsheet IDs, tokens, or credentials.
- Redact sheet IDs as `<SHEET_ID_REDACTED>`.
- Redact emails if present.
