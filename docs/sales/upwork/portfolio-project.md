# Upwork Portfolio Project — Google Workspace Automation Engine

This file is a copy/paste source for an Upwork portfolio entry. Keep the proof notes and limitations when adapting it; remove repository links only if the destination field does not support them.

## Portfolio project title

Google Workspace Automation: Gmail Intake and Sheets Data Cleanup

## Short subtitle

Auditable Python workflows that turn inbox requests and inconsistent spreadsheet rows into structured, reviewable outputs.

## Category and skills tags

**Category positioning:** Google Workspace automation / scripting and workflow automation

**Suggested skills:** Python, Google Sheets, Gmail, Google APIs, Workflow Automation, Data Cleaning, API Integration, Business Process Automation, CSV, JSON

Confirm the closest available category and tag names in Upwork when publishing because marketplace options can change.

## Short overview

I built a Python automation engine for two recurring operations problems: cleaning inconsistent Google Sheets data and converting matching Gmail messages into a structured Sheets triage queue. Both workflows preserve exceptions for human review and produce logs, audit exports, run artifacts, and redacted proof screenshots. The portfolio evidence comes from controlled successful runs, including a live Gmail-to-Sheets test using the `cloud google acc` and a real Google Sheet.

## Business problem

Teams often rely on Gmail and Google Sheets for lead intake, service requests, order tracking, finance review, and reporting. As volume grows, manual copy/paste and ad hoc spreadsheet cleanup create duplicate records, missing fields, inconsistent formats, missed follow-up, and little evidence of what changed.

The goal of this project was to make those processes repeatable and inspectable while keeping uncertain or invalid data visible to an operator.

## Solution delivered

The engine runs configured Google Workspace workflows through a shared command-line interface. Each run receives an ID and can produce structured logs, step records, workflow artifacts, error outputs, and JSON/CSV audit exports.

Two workflows were implemented and proven:

1. **Sheets cleanup and reporting** — normalizes rows, validates required fields and types, separates invalid rows, removes duplicates, and creates report and needs-review outputs.
2. **Gmail to Sheets intake** — searches Gmail, extracts structured fields, upserts a triage row by message ID, records parser quality, applies a processing label, and writes action/audit artifacts.

## What the automation does

### Sheets cleanup and reporting

- reads rows from a configured Google Sheet
- normalizes configured strings, dates, and numbers
- validates required fields and data types
- sends invalid rows to a needs-review output with explicit reasons
- removes duplicate validated rows using normalized keys
- writes cleanup metrics and review outputs to Google Sheets and per-run artifacts
- records logs and exports step-level audit data

### Gmail to Sheets intake

- searches Gmail with a configured query
- fetches and parses matching messages into a consistent row shape
- records parser confidence and structured errors
- upserts rows into a Google Sheets triage tab by Gmail message ID
- classifies outcomes and applies configured Gmail labels
- supports optional archive behavior through configuration
- writes triage, action, log, and audit artifacts

## Proof-backed highlights

### Sheets cleanup proof

Controlled run `fc494290d5ae48a69554e741d9ef530b` completed with status `SUCCESS`.

| Measure | Verified result |
| --- | ---: |
| Input rows | 5 |
| Invalid rows surfaced | 3 |
| Duplicate rows removed | 1 |
| Clean rows produced | 2 |
| Needs-review rows produced | 3 |

The audit recorded `validate_config=OK` and `run_cleanup=OK`. Invalid rows remained available with specific reasons rather than being silently discarded.

### Gmail-to-Sheets proof

The live proof used the `cloud google acc`, one controlled Gmail test message, and a real Google Sheets triage tab. Run `2c522287aa004b389d8fb49daa2ba164` completed with status `OK`.

| Check | Verified result |
| --- | --- |
| Gmail search | 1 message found |
| Gmail fetch | 1 message returned |
| Parser | Confidence `1.0`; no errors |
| Triage export | 1 data row with status `NEW` |
| Triage audit | 1 row with outcome `processed` |
| Gmail action | `label:gw/processed` |
| Audit export | `audit.json` and `audit.csv` created |

These are controlled portfolio results, not claims about production volume or a client deployment.

## Screenshots and evidence

### Sheets cleanup and reporting

- [Complete proof](../../../runs/_evidence/06.03.01.P01.T02/proof.md)
- [Terminal success banner](../../../runs/_evidence/06.03.01.P01.T02/screenshots/01-terminal-success-banner.png)
- [Report tab](../../../runs/_evidence/06.03.01.P01.T02/screenshots/02-report-tab.png)
- [Needs-review tab](../../../runs/_evidence/06.03.01.P01.T02/screenshots/03-needs-review-tab.png)
- [Run artifacts](../../../runs/_evidence/06.03.01.P01.T02/screenshots/04-artifact-view.png)

### Gmail to Sheets intake

- [Complete proof](../../../runs/_evidence/06.03.01.P01.T03/proof.md)
- [Terminal validation](../../../runs/_evidence/06.03.01.P01.T03/screenshots/01-terminal-validation-pass.png)
- [Redacted Sheets triage row](../../../runs/_evidence/06.03.01.P01.T03/screenshots/02-sheets-triage-row-redacted.png)
- [Redacted Gmail processing label](../../../runs/_evidence/06.03.01.P01.T03/screenshots/03-gmail-test-message-label-redacted.png)
- [Run artifacts](../../../runs/_evidence/06.03.01.P01.T03/screenshots/04-run-artifacts-folder.png)
- [Detailed case study](../../case-studies/google-workspace-automation-engine.md)

## Tech stack

- Python 3.12+
- Google Gmail and Sheets APIs
- Google API Python Client, Google Auth, and OAuth
- YAML workflow configuration
- structured JSONL logs and JSON/CSV audit exports
- CSV and JSON workflow artifacts
- pytest, Ruff, and mypy quality gates
- `uv` for dependency and command management

## What a similar client could get

Final scope depends on the current process, data shape, Google Workspace permissions, and required exception handling. A similar engagement could include:

- mapping the current Gmail or Sheets process and defining acceptance criteria
- configuring or adapting one workflow for the client's fields, queries, labels, and Sheet tabs
- preserving rejected or uncertain items in a review queue
- adding structured logs and proof artifacts for handoff
- running a controlled demonstration against approved test data
- documenting setup, credential prerequisites, rerun behavior, and operator checks
- delivering a follow-up validation and handoff package

The work can be priced after scope, access, data volume, and integration requirements are confirmed.

## Honest limitations

- The portfolio evidence covers controlled successful runs, not sustained production operation or load testing.
- No client names, financial outcomes, or measured time savings are claimed.
- Live execution requires valid Google credentials, OAuth scopes, API access, and permission to the target resources.
- Normal automated tests use fixture-backed coverage and exclude credentialed integration tests by default.
- Deployment packaging and scheduling are not currently documented; the proven workflows run through local CLI commands or demo scripts.
- Gmail archive, attachment, and alert capabilities are configurable, but they were not part of the one-message successful result summarized above.
- Exact parsing, validation, routing, and exception rules must be confirmed for each client process.

## Suggested Upwork image order

Use the clearest business output first and technical proof later. Suggested order and captions:

1. [Sheets report tab](../../../runs/_evidence/06.03.01.P01.T02/screenshots/02-report-tab.png) — "Cleanup report with input, invalid, duplicate, and clean-row metrics"
2. [Redacted Gmail-to-Sheets triage row](../../../runs/_evidence/06.03.01.P01.T03/screenshots/02-sheets-triage-row-redacted.png) — "Structured triage row created from a controlled Gmail message"
3. [Sheets needs-review tab](../../../runs/_evidence/06.03.01.P01.T02/screenshots/03-needs-review-tab.png) — "Invalid rows retained with reasons for human review"
4. [Redacted Gmail processing label](../../../runs/_evidence/06.03.01.P01.T03/screenshots/03-gmail-test-message-label-redacted.png) — "Gmail message marked with the configured processing label"
5. [Sheets terminal success](../../../runs/_evidence/06.03.01.P01.T02/screenshots/01-terminal-success-banner.png) — "Successful cleanup run and audit export paths"
6. [Gmail terminal validation](../../../runs/_evidence/06.03.01.P01.T03/screenshots/01-terminal-validation-pass.png) — "Validation pass for the live controlled Gmail-to-Sheets run"
7. [Sheets artifacts](../../../runs/_evidence/06.03.01.P01.T02/screenshots/04-artifact-view.png) — "Per-run report, review, log, and audit evidence"
8. [Gmail-to-Sheets artifacts](../../../runs/_evidence/06.03.01.P01.T03/screenshots/04-run-artifacts-folder.png) — "Triage, action, log, and audit artifacts"

Review each image at upload size and retain the redacted versions. Do not upload local configuration, private identifiers, OAuth material, or unreviewed operational artifacts.
