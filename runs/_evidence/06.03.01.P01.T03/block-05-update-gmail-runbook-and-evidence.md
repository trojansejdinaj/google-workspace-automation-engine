# 06.03.01.P01.T03 - Block 05 Update Gmail Runbook and Evidence

Calendar block: Update Gmail Runbook and Evidence

Parent task: 06.03.01.P01.T03 - Prove Gmail to Sheets Intake Workflow

Branch: task/06.03.01.P01.T03-gmail-workflow-demo-setup

Base local commit before block: e57f15e

## Scope

Update Gmail workflow documentation and evidence so the proven live Gmail-to-Sheets intake path is repeatable.

## Result

Updated `docs/runbooks/gmail_to_sheets_intake.md` with a live proof section covering:

- cloud google acc proof setup
- local-only credential/config rules
- required OAuth scopes
- Sheet triage tab setup
- controlled proof Gmail query
- controlled proof message
- demo command
- validation expectations
- troubleshooting notes

## Final successful live run

- Run ID: `2c522287aa004b389d8fb49daa2ba164`
- Gmail messages found: `1`
- Gmail messages fetched: `1`
- Triage rows written: `1`
- Audit rows: `1`
- Gmail action: `label:gw/processed`

## Block result

Block 05 makes the Gmail-to-Sheets live proof path repeatable and ties the runbook to the captured T03 evidence.
