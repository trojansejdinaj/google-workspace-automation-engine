# 06.03.01.P01.T03 - Block 01 Gmail Workflow Demo Setup

Calendar block: Gmail Workflow Demo Setup

Parent task: 06.03.01.P01.T03 - Prove Gmail to Sheets Intake Workflow

Branch: task/06.03.01.P01.T03-gmail-workflow-demo-setup

Base commit: 6b6483e

## Scope

Reviewed the Gmail intake workflow docs, config, OAuth requirements, sample assets, fixture coverage, expected outputs, and run command before executing the end-to-end demo.

## Discovered workflow files

- src/gw_engine/workflows/gmail_to_sheets_intake.py
- workflows/gmail_to_sheets_intake/README.md
- workflows/gmail_to_sheets_intake/config.example.yml
- workflows/gmail_to_sheets_intake/demo.sh
- docs/runbooks/gmail_to_sheets_intake.md
- docs/assets/gmail_to_sheets_intake/
- scripts/dump_gmail_fixtures.py
- Gmail-related tests under tests/ and tests/unit/

## Setup findings

The Gmail-to-Sheets workflow already has implementation, documentation, config example, demo script, auth guidance, sample assets, and targeted tests.

The live path requires:

- Gmail OAuth with gmail.modify scope for labels/archive actions.
- Sheets write access for the target spreadsheet.
- Local config copied from workflows/gmail_to_sheets_intake/config.example.yml.
- A real sheets.sheet_id.
- A safe gmail.gmail_query.
- Gmail labels for success, needs-review, and error routing.

A local config file exists at workflows/gmail_to_sheets_intake/config.local.yml and must not be committed.

## Demo strategy

Block 2 should run the documented demo path:

cd workflows/gmail_to_sheets_intake
bash ./demo.sh

If live Gmail/Sheets credentials are not ready or would expose sensitive data, Block 2 should use the safest fixture-backed/demo path and capture generated artifacts instead of production data.

## Evidence captured

- Raw setup inspection: runs/_evidence/06.03.01.P01.T03/raw/block-01-inspection.txt
- Targeted test output: runs/_evidence/06.03.01.P01.T03/raw/block-01-targeted-tests.txt

## Validation

Targeted Gmail intake checks passed:

- tests/test_gmail_decode.py
- tests/test_gmail_actions.py
- tests/unit/test_email_parser_p03_t3.py
- tests/unit/test_gmail_to_sheets_intake_workflow_audit.py
- tests/unit/test_gmail_to_sheets_intake_workflow_alerts.py
- tests/unit/test_gmail_to_sheets_intake_workflow_attachments.py

Result: 22 passed.

## Block result

Block 1 confirms the workflow surface area, docs, config, credential requirements, runbook, sample assets, and targeted test coverage needed before executing the Gmail intake demo.

## Next block

Block 2 should run the Gmail intake demo or fixture-backed fallback end-to-end and capture the generated run ID, artifacts, logs, audit files, triage output, and any blockers.
