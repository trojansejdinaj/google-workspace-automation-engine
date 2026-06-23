# 06.03.01.P01.T03 - Block 04 Capture Gmail Workflow Screenshots

Calendar block: Capture Gmail Workflow Screenshots

Parent task: 06.03.01.P01.T03 - Prove Gmail to Sheets Intake Workflow

Branch: task/06.03.01.P01.T03-gmail-workflow-demo-setup

Base local commit before block: c6e14a5

## Scope

Capture screenshot evidence for the live Gmail-to-Sheets intake workflow with sensitive values redacted.

## Screenshots captured

- `runs/_evidence/06.03.01.P01.T03/screenshots/01-terminal-validation-pass.png`
  - Shows terminal validation result with `VALIDATION_RESULT=PASS`
  - Shows final run ID `2c522287aa004b389d8fb49daa2ba164`

- `runs/_evidence/06.03.01.P01.T03/screenshots/02-sheets-triage-row-redacted.png`
  - Shows Google Sheets `triage` tab
  - Shows one generated triage row from the controlled test message
  - Shows parsed fields including subject, name, company, phone, amount, and invoice data
  - Uses controlled demo data only

- `runs/_evidence/06.03.01.P01.T03/screenshots/03-gmail-test-message-label-redacted.png`
  - Shows the controlled Gmail test message
  - Shows subject `GW Intake Test Lead`
  - Shows workflow-applied label `gw/processed`
  - Real account identifier is redacted

- `runs/_evidence/06.03.01.P01.T03/screenshots/04-run-artifacts-folder.png`
  - Shows final run artifacts under `runs/2c522287aa004b389d8fb49daa2ba164`
  - Includes actions artifacts, Gmail intake artifacts, parsed email output, triage audit, triage export, audit exports, logs, run metadata, and steps metadata

## Redaction notes

Screenshots avoid exposing OAuth credentials, refresh tokens, client secrets, Sheet IDs, browser URLs with sensitive IDs, and real private email addresses.

The visible email `demo.client@example.com` is controlled test data from the demo message and not a real private mailbox.

## Block result

Block 04 provides screenshot proof that the live Gmail-to-Sheets workflow passed validation, wrote the controlled parsed lead to the Sheet, applied the Gmail processed label, and generated the expected run artifacts.
EOFcd ~/projects/google-workspace-automation-engine

cat > runs/_evidence/06.03.01.P01.T03/block-04-capture-gmail-workflow-screenshots.md <<'EOF'
# 06.03.01.P01.T03 - Block 04 Capture Gmail Workflow Screenshots

Calendar block: Capture Gmail Workflow Screenshots

Parent task: 06.03.01.P01.T03 - Prove Gmail to Sheets Intake Workflow

Branch: task/06.03.01.P01.T03-gmail-workflow-demo-setup

Base local commit before block: c6e14a5

## Scope

Capture screenshot evidence for the live Gmail-to-Sheets intake workflow with sensitive values redacted.

## Screenshots captured

- `runs/_evidence/06.03.01.P01.T03/screenshots/01-terminal-validation-pass.png`
  - Shows terminal validation result with `VALIDATION_RESULT=PASS`
  - Shows final run ID `2c522287aa004b389d8fb49daa2ba164`

- `runs/_evidence/06.03.01.P01.T03/screenshots/02-sheets-triage-row-redacted.png`
  - Shows Google Sheets `triage` tab
  - Shows one generated triage row from the controlled test message
  - Shows parsed fields including subject, name, company, phone, amount, and invoice data
  - Uses controlled demo data only

- `runs/_evidence/06.03.01.P01.T03/screenshots/03-gmail-test-message-label-redacted.png`
  - Shows the controlled Gmail test message
  - Shows subject `GW Intake Test Lead`
  - Shows workflow-applied label `gw/processed`
  - Real account identifier is redacted

- `runs/_evidence/06.03.01.P01.T03/screenshots/04-run-artifacts-folder.png`
  - Shows final run artifacts under `runs/2c522287aa004b389d8fb49daa2ba164`
  - Includes actions artifacts, Gmail intake artifacts, parsed email output, triage audit, triage export, audit exports, logs, run metadata, and steps metadata

## Redaction notes

Screenshots avoid exposing OAuth credentials, refresh tokens, client secrets, Sheet IDs, browser URLs with sensitive IDs, and real private email addresses.

The visible email `demo.client@example.com` is controlled test data from the demo message and not a real private mailbox.

## Block result

Block 04 provides screenshot proof that the live Gmail-to-Sheets workflow passed validation, wrote the controlled parsed lead to the Sheet, applied the Gmail processed label, and generated the expected run artifacts.
