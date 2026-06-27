# Google Workspace Automation Engine

An auditable Python automation engine for turning repetitive Gmail and Google Sheets work into repeatable, reviewable workflows. This portfolio project focuses on practical operations outcomes: clean spreadsheet data, structured inbox intake, visible exceptions, and evidence that shows what each run did.

## Business problem

Small businesses and operations teams often run critical processes through inboxes and spreadsheets. As volume grows, manual copy/paste and ad hoc cleanup create predictable problems:

- inconsistent or duplicate records
- missed emails and incomplete follow-up data
- silent data loss when invalid rows are discarded
- no reliable record of what an automation changed
- time spent rebuilding the same operational report or triage queue

## Solution

The engine runs configured Google Workspace workflows through a common CLI and records each run. Workflows validate inputs, separate exceptions for human review, update operational Sheets or Gmail labels, and write structured logs and audit artifacts.

The portfolio currently contains two proven workflows:

| Workflow | Business outcome | Proven result |
| --- | --- | --- |
| `sheets_cleanup_reporting` | Converts messy Sheet rows into clean output, a needs-review queue, and cleanup metrics | Live end-to-end run completed with `SUCCESS` |
| `gmail_to_sheets_intake` | Converts matching Gmail messages into a structured Sheets triage queue and applies a processing label | Live Gmail and Sheets run completed with status `OK` |

`drive_intake_validator` is an early scaffold/configuration example. It is not presented as a proven live workflow.

## Workflow 1: Sheets cleanup + reporting

### Business problem solved

Spreadsheet data drifts over time: required fields go missing, numbers and dates use mixed formats, and duplicate records make reports unreliable. Cleaning this by hand is slow, inconsistent, and difficult to audit.

### What it does

The workflow:

1. reads rows from a configured Google Sheet
2. normalizes strings, dates, and numbers
3. validates required fields and data types
4. preserves invalid rows with explicit reasons in a needs-review output
5. removes duplicates from validated rows
6. writes report and needs-review outputs to Google Sheets and per-run artifacts

Useful client scenarios include CRM import preparation, billing or finance review, contact-list cleanup, reporting input validation, and quality checks before downstream automation.

### Validated proof and results

The proven run is `fc494290d5ae48a69554e741d9ef530b` with status `SUCCESS`.

| Measure | Validated result |
| --- | ---: |
| Rows in | 5 |
| Invalid rows | 3 |
| Duplicates removed | 1 |
| Clean rows out | 2 |
| Needs-review rows | 3 |

The audit recorded `validate_config=OK` and `run_cleanup=OK`. The report explains the cleanup funnel, while the needs-review output keeps row-level reasons so an operator can correct source data instead of losing it silently.

### Screenshots and evidence

![Sheets cleanup terminal success](runs/_evidence/06.03.01.P01.T02/screenshots/01-terminal-success-banner.png)

![Sheets cleanup report tab](runs/_evidence/06.03.01.P01.T02/screenshots/02-report-tab.png)

- [Complete Sheets workflow proof](runs/_evidence/06.03.01.P01.T02/proof.md)
- [Needs-review screenshot](runs/_evidence/06.03.01.P01.T02/screenshots/03-needs-review-tab.png)
- [Run artifact screenshot](runs/_evidence/06.03.01.P01.T02/screenshots/04-artifact-view.png)
- [Workflow documentation](workflows/sheets_cleanup_reporting/README.md)
- [Operator runbook](docs/runbooks/sheets-cleanup-reporting.md)
- [Sanitized sample assets](docs/assets/sheets_cleanup_reporting/README.md)
- [Sample cleanup report](docs/assets/sheets_cleanup_reporting/sample_report.csv)
- [Sample needs-review output](docs/assets/sheets_cleanup_reporting/sample_needs_review.csv)

## Workflow 2: Gmail to Sheets intake

### Business problem solved

Important requests, leads, invoices, and orders arrive in an inbox but often need to be tracked in a shared queue. Manual transfer into a spreadsheet is error-prone, hard to monitor, and gives reviewers no consistent signal that a message was processed.

### What it does

The workflow:

1. searches Gmail with a configured query
2. fetches matching messages and extracts structured fields
3. records parser confidence and structured parsing errors
4. upserts messages into a Google Sheets triage tab by message ID
5. applies configured Gmail labels and optional archive actions
6. writes triage, action, log, and audit artifacts for review

Useful client scenarios include lead intake, invoice or order capture, service-request triage, and shared follow-up queues.

### Validated proof and results

The live proof used the `cloud google acc`, one controlled Gmail test message, and a real Google Sheets triage tab. The documented successful run is `2c522287aa004b389d8fb49daa2ba164` with status `OK`.

| Check | Validated result |
| --- | --- |
| Gmail search | 1 message found |
| Gmail fetch | 1 message returned |
| Parser | Confidence `1.0`; no errors |
| Triage export | 1 data row with status `NEW` |
| Triage audit | 1 row with outcome `processed` |
| Gmail action | `label:gw/processed` |
| Audit export | `audit.json` and `audit.csv` exported successfully |

### Screenshots and evidence

![Gmail to Sheets validation](runs/_evidence/06.03.01.P01.T03/screenshots/01-terminal-validation-pass.png)

![Sheets triage row, redacted](runs/_evidence/06.03.01.P01.T03/screenshots/02-sheets-triage-row-redacted.png)

- [Complete Gmail workflow proof](runs/_evidence/06.03.01.P01.T03/proof.md)
- [Gmail processing label screenshot, redacted](runs/_evidence/06.03.01.P01.T03/screenshots/03-gmail-test-message-label-redacted.png)
- [Run artifacts screenshot](runs/_evidence/06.03.01.P01.T03/screenshots/04-run-artifacts-folder.png)
- [Workflow documentation](workflows/gmail_to_sheets_intake/README.md)
- [Operator and live-proof runbook](docs/runbooks/gmail_to_sheets_intake.md)
- [Portfolio asset capture guide](docs/assets/gmail_to_sheets_intake/README.md)

## Evidence model

Every execution receives a `run_id` and writes operational output under `runs/<run_id>/`. These generated run directories are intentionally ignored by git because they can contain environment-specific operational data.

Curated, redacted proof is stored under `runs/_evidence/`. A proof pack can include validation notes, selected screenshots, and sanitized outputs. This separates reproducible portfolio evidence from credentials, live identifiers, and unreviewed run data.

## Tech stack

- Python 3.12+ and `uv` for runtime and dependency management
- Google API Python Client with Google Auth and OAuth support
- Gmail, Google Sheets, and Drive client construction
- YAML-based workflow configuration and environment-based local settings
- structured JSONL logs plus JSON/CSV audit exports
- `pytest`, Ruff, and mypy for tests, formatting/linting, and strict type checking

The engine architecture, run model, authentication, retries, and logging contracts are documented in the [architecture overview](docs/architecture/00-system-overview.md).

## Setup and security notes

Install dependencies and create a local environment file:

```bash
uv sync
cp .env.example .env
```

Copy a workflow's `config.example.yml` to `config.local.yml` before a live run and add only local values there. The target Sheet or Drive resource must be shared with the active credential identity. Gmail actions require OAuth user credentials with the documented Gmail permissions.

Never commit `.env`, `config.local.yml`, OAuth client files, refresh tokens, real Sheet IDs, real Gmail account identifiers, or generated `runs/<run_id>/` directories. See [Google authentication](docs/architecture/05-auth.md) and [environment loading](docs/architecture/06-env-loading.md) for supported local configuration.

## Demo commands

Run the deterministic engine demo, which does not call live Google APIs:

```bash
uv run gw demo
```

Run the Sheets workflow after local auth and configuration are ready:

```bash
bash workflows/sheets_cleanup_reporting/demo.sh
```

Run the Gmail workflow after local OAuth and configuration are ready:

```bash
bash workflows/gmail_to_sheets_intake/demo.sh
```

Use the [deterministic demo runbook](docs/runbooks/demo-e2e.md) or the workflow-specific runbooks linked above for prerequisites and expected outputs.

## Audit export

Export step-level audit data for an existing local run:

```bash
uv run gw export <run_id> --format json
uv run gw export <run_id> --format csv
```

The default destinations are `runs/<run_id>/audit.json` and `runs/<run_id>/audit.csv`.

## Logs and outputs

A normal engine run writes these core files:

- `runs/<run_id>/run.json` — run metadata and final status
- `runs/<run_id>/steps.json` — step execution records
- `runs/<run_id>/logs.jsonl` — structured events with timestamp, level, component, event, and run ID
- `runs/<run_id>/artifacts/` — workflow-specific reports, triage exports, action records, and indexes
- `runs/<run_id>/errors/` — the run's error output directory

Exact workflow outputs are documented in each workflow README and runbook.

## Testing

Run the normal local/CI suite:

```bash
uv run pytest
```

Integration tests are deselected by default. They require real Google credentials and resources supplied through local environment variables:

```bash
uv run pytest -m integration
```

## Quality gates

Run the repository checks before committing code or documentation:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy . --no-incremental
uv run pytest
git diff --check
```

## Documentation index

- [Portfolio case study](docs/case-studies/google-workspace-automation-engine.md)
- [System overview](docs/architecture/00-system-overview.md)
- [Run model](docs/architecture/02-run-model.md)
- [Workflow plugin architecture](docs/architecture/03-workflow-plugin-architecture.md)
- [Logging contract](docs/architecture/04-logging-contract.md)
- [Authentication](docs/architecture/05-auth.md)
- [Engine execution contract](docs/architecture/08-engine-execution-contract.md)
- [Sheets validation model](docs/architecture/09-sheets-schema-validation.md)
- [Sheets cleanup runbook](docs/runbooks/sheets-cleanup-reporting.md)
- [Gmail intake runbook](docs/runbooks/gmail_to_sheets_intake.md)
- [Known limitations](docs/known-limitations.md)

## Known limitations

- Live workflows depend on valid local credentials, OAuth scopes, resource sharing, and Google API access.
- The normal test suite uses fixture-backed coverage and excludes live integration tests by default.
- Gmail label, archive, attachment, and alert behavior depends on mailbox permissions and configuration.
- Deployment packaging and scheduling are not documented; workflows currently run through local CLI commands or demo scripts.
- `drive_intake_validator` remains an early scaffold and should be verified before live use.

The maintained source of truth is [docs/known-limitations.md](docs/known-limitations.md).

## Future scope

Potential next steps, not current capabilities, are:

- package a documented deployment and scheduling path
- complete and prove the Drive intake validator before presenting it as production-ready
- expand automated live integration coverage in credentialed environments
- add further client-specific workflow configurations without weakening the shared audit and security model
