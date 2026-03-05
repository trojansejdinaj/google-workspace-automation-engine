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

### Actions (T5): labels + optional archive
- Classification:
  - `success` if `errors == 0` and `confidence >= min_confidence`
  - `needs_review` otherwise
- Labels used:
  - `gmail.labels.success`
  - `gmail.labels.needs_review`
- Optional archive behavior:
  - `archive_on_success` removes `INBOX` from success items.
  - `archive_on_failure` removes `INBOX` from needs_review items.
- Gmail scope requirement: `https://www.googleapis.com/auth/gmail.modify` (labels/archive actions).

## Attachments (T6)

Optional attachment support is controlled by `gmail_to_sheets_intake` config:

```yaml
attachments:
  enabled: false
  max_size_bytes: 5242880
  allowed_mime_types:
    - "application/pdf"
    - "image/jpeg"
    - "image/png"
  allowed_extensions:
    - ".pdf"
    - ".jpg"
    - ".png"
  route_mode: "artifacts" # artifacts | drive
  drive_folder_id: ""
```

When enabled, step `attachments` runs after parsing and triage upsert and for each matched message:
1) list attachments via Gmail API
2) download each attachment body
3) validate against size + MIME/extension allowlist
4) invalid -> quarantine to `runs/<run_id>/attachments/quarantine/`
5) valid -> route to:
   - `runs/<run_id>/attachments/routed/` if `route_mode: artifacts`
   - Drive folder `drive_folder_id` if `route_mode: drive`

Run outputs include:
- `runs/<run_id>/attachments/raw/` (downloaded bytes)
- `runs/<run_id>/attachments/quarantine/`
- `runs/<run_id>/attachments/routed/` (for artifacts mode)
- `runs/<run_id>/attachments/manifest.jsonl` (per-attachment status + sha256)
- `runs/<run_id>/attachments/summary.jsonl` (attachment processing run-summary)

Artifact index entries added by this step:
- `attachments_manifest_jsonl` for manifest
- `attachments_summary_jsonl` for summary

Attachment summary logs:
- `gmail_attachments_summary` event includes `total`, `routed`, `quarantined`, `errors`.

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
- Fill `runs/_evidence/01.04.02.P03.T5-check-proof.txt`.
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

## Evidence (T5)
Use `runs/_evidence/01.04.02.P03.T5-check-proof.txt` with:
1) redacted config dump (`gmail_query`, `gmail.labels`, `options`)
2) 5–10 `apply_actions` log lines (or equivalent step summary lines)
3) output snippet from `artifacts/actions_plan.json` or `artifacts/actions_applied.json`
