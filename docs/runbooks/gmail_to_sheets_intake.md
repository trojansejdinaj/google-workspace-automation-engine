# Gmail to Sheets Intake Runbook

Purpose: how to run [gmail_to_sheets_intake](../../workflows/gmail_to_sheets_intake/README.md), inspect outputs, and capture safe local evidence.

## 1) Purpose + when to run

Use this runbook when you need to:
- run Gmail search/fetch/parsing into a Sheets triage tab
- apply configured Gmail labels and optional archive actions
- verify artifacts, logs, and audit output
- capture redacted proof for historical evidence

The workflow is implemented for live Google API execution when OAuth credentials, Sheets access, and Gmail permissions are configured. Fixture-backed tests cover parsing, attachments, alerts, and action behavior without calling live Google APIs.

## 2) Prereqs

- Auth/env setup: see [Google auth](../architecture/05-auth.md) and [environment loading](../architecture/06-env-loading.md).
- Sheet permissions: the target Sheet must be shared with the credential identity used locally.
- Label existence: confirm configured Gmail labels exist (or can be created) and names match config exactly.
- Local config: copy [config.example.yml](../../workflows/gmail_to_sheets_intake/config.example.yml) to `workflows/gmail_to_sheets_intake/config.local.yml` and keep local values out of git.

## 3) Steps

```bash
cd workflows/gmail_to_sheets_intake
cp -n config.example.yml config.local.yml
```

Edit `config.local.yml`:
- set `sheets.sheet_id`
- set `gmail.gmail_query`
- set label names under `gmail.labels`

Run from repo root or workflow folder:

```bash
bash ./demo.sh
```

## 4) What success looks like

- Demo command exits with status 0.
- A new run directory is created at `runs/<run_id>/`.
- Logs are present at `runs/<run_id>/logs.jsonl`.
- Artifacts may include `triage_export.csv`, `triage_audit.jsonl`, `actions_plan.json`, `actions_applied.json`, attachment manifests, and alert JSON depending on config.
- `audit.json` / `audit.csv` may also appear under `runs/<run_id>/` after `uv run gw export <run_id>`.

## 5) Common failures + fixes

- Auth errors (`unauthorized`, token issues): verify local auth/env setup and retry.
- Permission denied on Sheet: share the spreadsheet with the active credential identity.
- Missing/invalid `sheet_id`: update `sheets.sheet_id` in `config.local.yml`.
- Label not found / label mismatch: create labels or fix names in `gmail.labels`.
- Command failure from wrong directory: run `bash ./demo.sh` from `workflows/gmail_to_sheets_intake/`.

## 6) Evidence (P03.T1)

Historical scaffold proof remains at:
- [P03.T1 proof](../../runs/_evidence/01.04.02.P03.T1-proof.txt)

Include:
- redacted config dump (`config.local.yml`, no secrets)
- 5–10 log lines from `runs/<run_id>/logs.jsonl` (or CLI output)
- output snippet showing `runs/<run_id>/` path (or artifacts index line)

## Live proof run: cloud google acc Gmail to Sheets

This live proof path was used for task `06.03.01.P01.T03`.

### Local-only files

Do not commit `.env`, `config.local.yml`, OAuth client JSON files, refresh-token files, real Sheet IDs, or real Gmail account identifiers. The local workflow config is ignored by git via `**/config.local.yml`.

### Required OAuth scopes

The Gmail workflow applies labels and may optionally archive messages, so Gmail OAuth must use `https://www.googleapis.com/auth/gmail.modify`.

The full live proof token should include Gmail modify, Google Sheets, and Drive file access.

### Sheet setup

Create a Google Sheet in the cloud google acc and add a tab named exactly `triage`.

### Controlled proof query

For repeatable proof runs, use this local Gmail query:

`subject:"GW Intake Test Lead" newer_than:1d`

Use labels:

- success: `gw/processed`
- needs review: `gw/needs-review`
- error: `gw/error`

Keep archive behavior disabled for proof runs:

- `archive_on_success: false`
- `archive_on_failure: false`

### Controlled proof message

Subject: `GW Intake Test Lead`

Body should include demo lead fields for name, company, email, phone, amount, and invoice/order ID.

The T03 proof run used:

- Name: Demo Client
- Company: Acme Roofing
- Email: demo.client@example.com
- Phone: +355 68 000 0000
- Amount: 1250
- Invoice: INV-1001

### Demo command

Run from the repository root:

`bash workflows/gmail_to_sheets_intake/demo.sh`

Expected result is `ok: true` with a generated run ID.

### Validation expectations

For the controlled proof run, confirm:

- Gmail search found 1 message
- Gmail fetch returned 1 message
- parsed_emails.jsonl has 1 row
- Parser confidence is 1.0
- Parser errors are empty
- triage_export.csv has 1 data row
- Triage status is NEW
- triage_audit.jsonl has 1 row
- Audit outcome is processed
- Audit includes label:gw/processed
- actions_plan.json has success_count 1
- actions_applied.json has actions_success_count 1
- audit.json and audit.csv export successfully

### Troubleshooting

- invalid_grant: regenerate the cloud google acc OAuth refresh token.
- invalid_scope: confirm OAuth includes gmail.modify, spreadsheets, and drive.file.
- Unable to parse range: triage!A1:Z: create or rename the Sheet tab to exactly triage.
- ids_found: 0: send the controlled test email and use the narrow subject query.
- Labels not applied: confirm Gmail OAuth uses gmail.modify, not gmail.readonly.
