# 06.03.01.P01.T03 - Block 02 Run Gmail Intake Demo

Calendar block: Run Gmail Intake Demo

Parent task: 06.03.01.P01.T03 - Prove Gmail to Sheets Intake Workflow

Branch: task/06.03.01.P01.T03-gmail-workflow-demo-setup

Base local commit before block: 873cdd5

## Scope

Execute the Gmail-to-Sheets intake workflow or fixture-backed demo. Confirm messages/leads are fetched or loaded, parsed, triaged, and written/exported without duplicate rows.

## Result

Block 02 completed with a real cloud google acc Gmail-to-Sheets run.

Final successful run:

- Run ID: `2c522287aa004b389d8fb49daa2ba164`
- Workflow: `gmail_to_sheets_intake`
- Status: `OK`
- Query: `subject:"GW Intake Test Lead" newer_than:1d`
- Gmail messages found: `1`
- Gmail messages fetched: `1`
- Plain bodies decoded: `1`
- Triage rows written: `1`
- Parsed email rows: `1`
- Triage audit rows: `1`
- Successful Gmail actions: `1`
- Needs-review actions: `0`
- Archive actions: `0`
- Attachments enabled: `false`

## Important implementation fix

The repo Gmail auth test path was still using the old read-only Gmail scope.

Changed:

- From: `https://www.googleapis.com/auth/gmail.readonly`
- To: `https://www.googleapis.com/auth/gmail.modify`

Reason:

The Gmail intake workflow labels messages and can optionally archive them. That requires `gmail.modify`. The cloud google acc OAuth token was granted `gmail.modify`, so the test path must use the same scope.

## Live run path

The workflow now runs against the cloud google acc:

- Gmail OAuth: cloud google acc OAuth client and refresh token in local `.env`
- Sheets target: cloud google acc Google Sheet
- Sheet tab: `triage`
- Local config: `workflows/gmail_to_sheets_intake/config.local.yml`
- Local config status: ignored by git

## Controlled test message

A controlled Gmail test message was sent to the cloud google acc with subject:

`GW Intake Test Lead`

The parser extracted:

- Name: Demo Client
- Company: Acme Roofing
- Phone: redacted in evidence
- Email: redacted in evidence
- Amount: 1250
- Invoice/order ID: INV-1001
- Confidence: 1.0
- Parser errors: none

## Generated artifacts

Final successful run generated:

- `runs/2c522287aa004b389d8fb49daa2ba164/artifacts/gmail_intake_items.json`
- `runs/2c522287aa004b389d8fb49daa2ba164/artifacts/gmail_intake_summary.json`
- `runs/2c522287aa004b389d8fb49daa2ba164/artifacts/parsed_emails.jsonl`
- `runs/2c522287aa004b389d8fb49daa2ba164/artifacts/triage_export.csv`
- `runs/2c522287aa004b389d8fb49daa2ba164/artifacts/triage_audit.jsonl`
- `runs/2c522287aa004b389d8fb49daa2ba164/artifacts/actions_plan.json`
- `runs/2c522287aa004b389d8fb49daa2ba164/artifacts/actions_applied.json`
- `runs/2c522287aa004b389d8fb49daa2ba164/audit.json`
- `runs/2c522287aa004b389d8fb49daa2ba164/audit.csv`
- `runs/2c522287aa004b389d8fb49daa2ba164/logs.jsonl`

## Evidence captured

Raw evidence files:

- `runs/_evidence/06.03.01.P01.T03/raw/block-02-demo-run.txt`
- `runs/_evidence/06.03.01.P01.T03/raw/block-02-live-failure-inspection.txt`
- `runs/_evidence/06.03.01.P01.T03/raw/block-02-gmail-oauth-cutover.txt`
- `runs/_evidence/06.03.01.P01.T03/raw/block-02-real-demo-run.txt`
- `runs/_evidence/06.03.01.P01.T03/raw/block-02-real-demo-retry.txt`
- `runs/_evidence/06.03.01.P01.T03/raw/block-02-real-success-artifact-inspection.txt`
- `runs/_evidence/06.03.01.P01.T03/raw/block-02-real-message-demo-run.txt`
- `runs/_evidence/06.03.01.P01.T03/raw/block-02-real-message-demo-retry.txt`
- `runs/_evidence/06.03.01.P01.T03/raw/block-02-real-message-artifact-inspection.txt`
- `runs/_evidence/06.03.01.P01.T03/raw/block-02-real-message-run-id.txt`

## Notes

Earlier live attempts exposed real blockers that were fixed during this block:

1. Gmail OAuth initially failed with `invalid_grant`.
2. The project was moved to the cloud google acc.
3. Gmail auth test initially failed with `invalid_scope` because `auth.py` still used `gmail.readonly`.
4. A real run failed because the Sheet tab `triage` did not exist.
5. A later real run succeeded but processed zero messages.
6. The final controlled-message run processed one real Gmail message end-to-end.

## Block result

Block 02 proves the live Gmail-to-Sheets intake path works against the cloud google acc with a controlled real Gmail message, a real Google Sheet, parsed lead fields, Sheet triage output, Gmail label action, triage audit output, action artifacts, logs, and exported audit files.

## Next block

Block 03 should validate parsed fields, parse confidence, parse errors, triage rows, message IDs, statuses, Gmail labels/actions, and export CSV quality.
