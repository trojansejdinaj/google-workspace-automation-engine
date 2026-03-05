# gmail_to_sheets_intake sample assets

This folder contains sanitized sample assets for portfolio/demo documentation.

## Files
- `01-terminal-run-success.png`
  - Screenshot of terminal output after `bash ./demo.sh`.
- `02-sheet-rows-created.png`
  - Screenshot of the triage tab after a run.
  - Show rows keyed by `message_id`, plus visible `gmail_link` and `status`.
- `03-gmail-label-or-archive.png`
  - Screenshot showing Gmail label and/or archive action results for one or more messages.
- `04-audit-snippet.png`
  - Screenshot of `runs/<run_id>/artifacts/triage_audit.jsonl` sample rows.

## Portfolio screenshots (required)
These `.png` files are placeholders and are intentionally empty until captured.

1) `01-terminal-run-success.png`
2) `02-sheet-rows-created.png`
3) `03-gmail-label-or-archive.png`
4) `04-audit-snippet.png`

## Reproduce with demo.sh
From repo root:

```bash
cd workflows/gmail_to_sheets_intake
bash ./demo.sh
```

After completion, note `run_id` from terminal output and collect evidence from:
- `runs/<run_id>/artifacts/triage_export.csv`
- `runs/<run_id>/artifacts/triage_audit.jsonl`
- `runs/_evidence/01.04.02.P03.T8-proof-pack.txt`

## Sanitization rules
- Do not include real spreadsheet IDs, tokens, or credentials.
- Redact sheet IDs as `<SHEET_ID_REDACTED>`.
- Redact emails if present.
