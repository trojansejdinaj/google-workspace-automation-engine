# gmail_to_sheets_intake

## Problem
Inbox triage is noisy and easy to drift:
- important emails are mixed with low-signal traffic
- key details are captured inconsistently (or not at all)
- reviewers lack a single queue for follow-up
- manual copy/paste is error-prone and hard to rerun safely

## Solution
This workflow will:
1) search Gmail using a configured query
2) parse selected email fields into a consistent row shape
3) upsert rows into Google Sheets for durable tracking
4) apply success/failure labels in Gmail for triage feedback
5) write per-run artifacts under `runs/<run_id>/` for auditability

## Gmail adapter: search + fetch + body decode
Supported in T2:
- Search messages with configured Gmail query inputs.
- Fetch message details needed for downstream parsing.
- Decode message body content from Gmail payload encoding.

## Parsing + Structured Extraction
- Parser code: `src/gw_engine/parsing/email_parser.py`.
- Attempted fields: `name`, `company`, `email`, `phone`, `amount`, `invoice_or_order_id` (label-first, then fallbacks).
- Confidence/errors: confidence is a normalized score in `[0,1]`; errors are structured with codes such as `missing_field`, `ambiguous_match`, and `invalid_format`.
- Parsed output artifact: `runs/<run_id>/artifacts/parsed_emails.jsonl` (PII-safe shape; excludes raw body text).
- Extending rules: add/update a label list or regex extractor in `email_parser.py`, then route it through `parse_email(...)` and add/update fixture tests.

## 2-minute demo (T1 scaffold)

```bash
cd workflows/gmail_to_sheets_intake
cp -n config.example.yml config.local.yml
```

Edit `config.local.yml` (local only):
- set `sheets.sheet_id`
- set `gmail.gmail_query`
- set Gmail label names for success/failure handling

Run:

```bash
bash ./demo.sh
```

T1 provides scaffold only. The demo command is in place and will run end-to-end once workflow implementation is added in later tasks.

## Run + Verify (T4)
1) Create local config from example:

```bash
cd workflows/gmail_to_sheets_intake
cp -n config.example.yml config.local.yml
```

Edit `config.local.yml` and set a redacted-safe value in docs/proof (do not commit real IDs):
- `sheets.sheet_id: <SHEET_ID_REDACTED>`

2) Run the workflow (repo CLI entrypoint):

```bash
uv run gw run gmail_to_sheets_intake --config workflows/gmail_to_sheets_intake/config.local.yml
```

3) Verification checklist:
- `triage` tab has rows keyed by `message_id`.
- `gmail_link` opens the matching Gmail message.
- `status` column exists and is preserved on rerun.
- `runs/<run_id>/artifacts/triage_export.csv` exists.

4) Evidence checklist:
- Fill `runs/_evidence/01.04.02.P03.T4-check-proof.txt`.
- Capture 1-2 screenshots to `docs/assets/gmail_to_sheets_intake/`.

Before committing, run:

```bash
make fmt
make lint
make test
```

## Expected outputs
Standard engine outputs under `runs/<run_id>/`:
- `logs.jsonl`
- `audit.json` / `audit.csv` (if export is available for the run)
- `artifacts/`
- `errors/`

## Troubleshooting
- Auth/env: ensure Google auth environment variables are configured for your local setup.
- Permissions: share the target Sheet with the credential identity used by the workflow.
- Gmail labels: confirm configured labels exist (or are creatable) and names match config exactly.

## Evidence (DoD proof)
Save proof file:
`runs/_evidence/01.04.02.P03.T1-proof.txt`

Include:
1) config dump (sanitized as needed)
2) 5–10 representative log lines
3) output snippet from run artifacts/audit output

## Proof / Evidence (T4)
Capture and store:
- `runs/<run_id>/artifacts/triage_export.csv` (or a short snippet from it)
- `runs/_evidence/01.04.02.P03.T4-check-proof.txt` (RESULT, redacted config, logs, output snippet)
- 1-2 screenshots in `docs/assets/gmail_to_sheets_intake/`:
	- `portfolio-01.png` (triage tab after run)
	- `portfolio-02.png` (artifacts view or opened `triage_export.csv` snippet)
