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
