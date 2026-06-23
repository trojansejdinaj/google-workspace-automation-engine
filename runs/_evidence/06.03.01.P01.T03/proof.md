# 06.03.01.P01.T03 - Prove Gmail to Sheets Intake Workflow

## Task

Prove Gmail-to-Sheets intake workflow.

## Definition of Done

Gmail-to-Sheets intake demo or fixture-backed demo runs end-to-end, parsed triage output is generated, logs/audit evidence exists, screenshots are captured with sensitive data redacted, runbook is updated, and the T03 proof file is saved.

## Final result

T03 is complete.

The live Gmail-to-Sheets workflow was proven against the cloud google acc using a controlled real Gmail message and a real Google Sheet.

Final successful live run:

- Run ID: `2c522287aa004b389d8fb49daa2ba164`
- Workflow: `gmail_to_sheets_intake`
- Status: `OK`
- Gmail query: `subject:"GW Intake Test Lead" newer_than:1d`
- Gmail messages found: `1`
- Gmail messages fetched: `1`
- Parsed email rows: `1`
- Parser confidence: `1.0`
- Parser errors: none
- Triage rows written: `1`
- Triage audit rows: `1`
- Gmail action: `label:gw/processed`
- Actions success count: `1`
- Needs-review count: `0`
- Audit exports: `audit.json` and `audit.csv`

## Implementation change

Updated Gmail OAuth scope in `src/gw_engine/auth.py` from Gmail read-only to Gmail modify.

Reason: the intake workflow applies Gmail labels and may optionally archive messages, so `gmail.modify` is required.

## Evidence by block

### Block 01 - Gmail Workflow Demo Setup

- Proof: `runs/_evidence/06.03.01.P01.T03/block-01-gmail-workflow-demo-setup.md`
- Confirmed workflow files, config example, demo script, runbook, assets, OAuth requirements, Sheets requirements, Gmail label requirements, and fixture-backed test coverage.
- Local commit: `873cdd5`

### Block 02 - Run Gmail Intake Demo

- Proof: `runs/_evidence/06.03.01.P01.T03/block-02-run-gmail-intake-demo.md`
- Proved live Gmail-to-Sheets run using cloud google acc.
- Generated parsed artifacts, triage output, Gmail action artifacts, audit artifacts, logs, and audit exports.
- Final run ID: `2c522287aa004b389d8fb49daa2ba164`
- Local commit: `b6a0f65`

### Block 03 - Validate Gmail Parsed Data and Triage

- Proof: `runs/_evidence/06.03.01.P01.T03/block-03-validate-gmail-parsed-data-and-triage.md`
- Validation result: `PASS`
- Confirmed parsed fields, confidence, parser errors, triage row, Gmail link, audit row, action plan, and action application.
- Local commit: `c6e14a5`

### Block 04 - Capture Gmail Workflow Screenshots

- Proof: `runs/_evidence/06.03.01.P01.T03/block-04-capture-gmail-workflow-screenshots.md`
- Screenshots:
  - `screenshots/01-terminal-validation-pass.png`
  - `screenshots/02-sheets-triage-row-redacted.png`
  - `screenshots/03-gmail-test-message-label-redacted.png`
  - `screenshots/04-run-artifacts-folder.png`
- Local commit: `e57f15e`

### Block 05 - Update Gmail Runbook and Evidence

- Proof: `runs/_evidence/06.03.01.P01.T03/block-05-update-gmail-runbook-and-evidence.md`
- Updated `docs/runbooks/gmail_to_sheets_intake.md` with repeatable live proof instructions.
- Local commit: `5b8ee96`

## Redaction and secret hygiene

Evidence avoids committing:

- `.env`
- `config.local.yml`
- OAuth client JSON files
- Refresh-token files
- Real Google Sheet IDs
- Real private Gmail account identifiers

Screenshots are redacted where needed. The visible `demo.client@example.com` value is controlled test data.

## Final DoD mapping

- End-to-end Gmail-to-Sheets demo run: complete
- Parsed triage output generated: complete
- Logs/audit evidence exists: complete
- Screenshots captured with sensitive values redacted: complete
- Runbook updated: complete
- T03 final proof file saved: complete

## Branch status

This task was completed locally on branch:

`task/06.03.01.P01.T03-gmail-workflow-demo-setup`

The branch should be pushed and opened as a PR only after this final block commit is created.
