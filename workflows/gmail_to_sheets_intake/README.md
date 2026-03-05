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

## Needs-review alert (T7)

- After `apply_actions`, the workflow can emit a needs-review alert when new needs-review items were created.
- Controlled by `alerts.enabled` and `alerts.include_total_count` in config.
- Alert step runs after routing/labeling (`apply_actions`), reads:
  - `needs_review_new_count` from state (set by `apply_actions`)
  - `sheets.sheet_id` + `sheets.tabs.triage_tab`
  - `gmail.labels.needs_review` for optional total count query
- If `needs_review_new_count == 0`, event `needs_review_alert_suppressed` is logged.
- If enabled and new count > 0:
  - writes `artifacts/needs_review_alert.json`
  - registers `needs_review_alert_json`
  - logs `needs_review_alert_emitted`
- If `alerts.include_total_count: true`, total count uses capped `GmailAdapter.search_message_ids(query=f"label:<needs_review_label>")`.

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

## 2-minute demo

From repo root:

```bash
cd workflows/gmail_to_sheets_intake
cp -n config.example.yml config.local.yml
```

Edit `config.local.yml` with your real values:
- `gmail.gmail_query`
- `sheets.sheet_id`
- `gmail.labels.success`
- `gmail.labels.needs_review`
- `gmail.labels.error`

Run:

```bash
uv run gw run gmail_to_sheets_intake --config workflows/gmail_to_sheets_intake/config.local.yml
```

After the run, collect:

```bash
uv run gw export <run_id> --format json
uv run gw export <run_id> --format csv
```

## Expected outputs

- `runs/<run_id>/artifacts/triage_export.csv`
  - Rows are upserted by `message_id` into the configured triage tab.
  - Expected columns include at least: `message_id`, `gmail_link`, `status`, `last_run_id`, `updated_at`.
  - Verify that new/updated rows have `status` and a non-empty `gmail_link`.
- `runs/<run_id>/artifacts/triage_audit.jsonl` (new in this task)
  - One row per message processed by `apply_actions` with required columns:
    - `run_id`
    - `message_id`
    - `outcome` (`processed` | `needs_review` | `skipped` | `error`)
    - `reason`
    - `sheet_row_id`
    - `gmail_actions` (e.g. `label:gw/processed`, `label:gw/needs-review`, `archive_inbox`)
    - `timestamp`
- `runs/<run_id>/artifacts/actions_plan.json` and `runs/<run_id>/artifacts/actions_applied.json`
  - Confirms `processed` and `needs_review` counts.
- `runs/<run_id>/audit.json` and `runs/<run_id>/audit.csv`
  - Engine step-level audit export from `gw export`.
  - Includes `step_name` and step-level status for every workflow step.
- `runs/<run_id>/artifacts/needs_review_alert.json` (created when alert fires)
- `runs/<run_id>/artifacts/triage_audit.jsonl` action fields and logs
  - Labels/actions to verify:
    - `needs_review` rows should include `label:<needs_review_label>` and optional `archive_inbox` when `archive_on_failure: true`.
    - `processed` rows should include `label:<success_label>` and optional `archive_inbox` when `archive_on_success: true`.
- `logs.jsonl` / console output
  - `gmail_actions_applied` and `apply_actions_done` confirm actions by bucket.

## Troubleshooting

- Auth/env not ready
  - Confirm Google credentials are available and valid for both Gmail and Sheets.
- Sheets permission denied / wrong sheet
  - Share the Sheet with the service account/user used by the workflow.
  - Verify `sheets.sheet_id` is valid and writable.
- Labels not found
  - Ensure `gmail.labels.success`, `gmail.labels.needs_review`, and `gmail.labels.error` match existing labels.
  - The workflow will auto-create labels if the account has permission.
- Query returns no rows
  - Use a broader `gmail.gmail_query` temporarily (`in:inbox`, `newer_than:1d`) and check `gmail_intake_summary`.
- Archive behavior feels wrong
  - Verify `archive_on_success` / `archive_on_failure` in `options` match desired behavior.

## Portfolio screenshots

Place 1–2 screenshots in:

`docs/assets/gmail_to_sheets_intake/`

Recommended files:
1) `01-terminal-run-success.png`
2) `02-sheet-rows-created.png`
3) `03-gmail-label-or-archive.png`
4) `04-audit-snippet.png`

Before committing, run:

```bash
make fmt
make lint
make test
```

## Evidence (T5)
Use `runs/_evidence/01.04.02.P03.T5-check-proof.txt` with:
1) redacted config dump (`gmail_query`, `gmail.labels`, `options`)
2) 5–10 `apply_actions` log lines (or equivalent step summary lines)
3) output snippet from `artifacts/actions_plan.json` or `artifacts/actions_applied.json`

## Evidence (T7)
Use `runs/_evidence/01.04.02.P03.T7-check-proof.txt` with:
1) alert output in logs (`needs_review_alert_emitted` or `needs_review_alert_suppressed`)
2) `artifacts/needs_review_alert.json` or evidence that no artifact exists when suppressed
3) triage sheet URL used in the alert payload

## Evidence (T8)
Use `runs/_evidence/01.04.02.P03.T8-proof-pack.txt` with:
1) sanitized config dump (query, labels, options)
2) copied demo commands above
3) 5–10 `triage_audit_written` / `apply_actions` / step summary log lines
4) output snippet from `artifacts/triage_audit.jsonl` showing `message_id` and `outcome`
