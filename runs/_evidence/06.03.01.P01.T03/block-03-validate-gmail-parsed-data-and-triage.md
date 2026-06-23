# 06.03.01.P01.T03 - Block 03 Validate Gmail Parsed Data and Triage

Calendar block: Validate Gmail Parsed Data and Triage

Parent task: 06.03.01.P01.T03 - Prove Gmail to Sheets Intake Workflow

Branch: task/06.03.01.P01.T03-gmail-workflow-demo-setup

Base local commit before block: b6a0f65

## Scope

Validate parsed Gmail data, parse confidence, parser errors, triage row output, message IDs, statuses, Gmail actions, and exported CSV quality from the real cloud google acc run.

## Validated run

- Run ID: `2c522287aa004b389d8fb49daa2ba164`
- Workflow: `gmail_to_sheets_intake`
- Status: `OK`
- Query: `subject:"GW Intake Test Lead" newer_than:1d`
- Controlled message subject: `GW Intake Test Lead`

## Validation results

The validation script confirmed:

- Run status is `OK`
- All workflow steps are `OK`
- Gmail search found `1` message
- Gmail fetch returned `1` message
- Plain-text body decode count is `1`
- `parsed_emails.jsonl` has `1` parsed row
- Parser confidence is `1.0`
- Parser errors are empty
- Name parsed as `Demo Client`
- Company parsed as `Acme Roofing`
- Amount parsed as `1250.0`
- Invoice/order ID parsed as `INV-1001`
- Email and phone fields are present
- `triage_export.csv` has `1` data row
- Triage row message ID matches parsed message ID
- Triage status is `NEW`
- Triage `last_run_id` matches the final run ID
- Triage Gmail link is present
- `triage_audit.jsonl` has `1` audit row
- Audit outcome is `processed`
- Audit includes `label:gw/processed`
- `actions_plan.json` has `success_count: 1`
- `actions_applied.json` has `actions_success_count: 1`
- Needs-review count is `0`

## Evidence captured

- Raw validation output: `runs/_evidence/06.03.01.P01.T03/raw/block-03-parse-triage-validation.txt`

## Block result

Block 03 confirms that the real Gmail-to-Sheets intake run produced valid parsed data, correct triage output, matching IDs, expected status, clean parser confidence/errors, expected Gmail label action, and audit/export artifacts.

## Next block

Block 04 should capture screenshots of the terminal proof, Sheet triage output, Gmail label/result, and audit/log evidence with sensitive values redacted.
