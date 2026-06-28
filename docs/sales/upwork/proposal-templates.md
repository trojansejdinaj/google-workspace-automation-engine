# Upwork Proposal Templates

Replace every bracketed placeholder before sending. Keep only the features that match the job, and confirm access, data shape, exception rules, and acceptance criteria before committing to scope or price.

## 1. Short proposal — Gmail to Sheets intake

Hi [client business],

I can help turn your [current Gmail process] into a structured Google Sheets queue without hiding messages that need manual review.

I have built and proven a Python Gmail-to-Sheets workflow that searches a configured query, extracts structured fields, upserts rows by Gmail message ID, records parser confidence/errors, applies processing labels, and writes audit artifacts. In a controlled live proof, it found and fetched one test message, created one `NEW` triage row, recorded a `processed` audit outcome, and applied the configured processing label.

For your workflow, I would first confirm the Gmail query, fields, target Sheet columns, duplicate behavior, labels, and review rules. Then I can propose a precise delivery scope for [desired output].

If you share a sample message with sensitive values removed and the desired Sheet layout, I can outline the implementation and validation plan.

## 2. Short proposal — messy spreadsheet cleanup and reporting

Hi [client business],

I can help make your [Google Sheet / spreadsheet process] repeatable by separating clean records from rows that need attention and producing a report that explains the result.

I have built and proven a Sheets cleanup workflow that normalizes configured values, validates required fields and types, removes duplicates, preserves rejected rows with reasons, and exports audit evidence. A controlled run evaluated 5 rows, surfaced 3 invalid rows, removed 1 duplicate, produced 2 clean rows, and retained 3 needs-review rows.

For your data, I would confirm the schema, accepted formats, deduplication keys, review reasons, output tabs, and rerun behavior before finalizing scope. Please send a redacted sample and the expected [desired output], and I can map the cleanup rules.

## 3. Short proposal — Google Workspace automation and audit

Hi [client business],

Your [current workflow] sounds like a good candidate for a focused Google Workspace automation audit before implementation.

I work with Python, Gmail, Google Sheets, Google APIs, structured logs, and JSON/CSV audit outputs. My portfolio project includes two controlled, proven workflows: Gmail-to-Sheets intake and Sheets cleanup/reporting. Both keep exceptions visible and produce evidence showing what each run did.

I would review the current steps, inputs, permissions, failure points, duplicate risks, and required human approvals. The output can be a scoped automation plan, risk list, proof-backed demo plan, and delivery estimate. Pricing can be confirmed after the number of workflows and integration constraints are clear.

## 4. Detailed proposal — higher-value lead

Hi [client business],

You need [current workflow] to produce [desired output] without relying on repeated copy/paste or leaving the team unsure about failures and exceptions.

I would approach this in four parts:

1. **Process and data mapping** — confirm the Gmail query or Sheet inputs, field schema, output destinations, duplicate rules, exception cases, and operator responsibilities.
2. **Controlled implementation** — configure or adapt the workflow against approved test data and a non-production target where practical.
3. **Validation and proof** — verify row counts, field mappings, labels/actions, review queues, rerun behavior, logs, and audit exports against agreed acceptance criteria.
4. **Handoff** — document credentials and permission prerequisites, configuration, run commands, expected outputs, troubleshooting, and any work that remains manual.

Relevant proof from my Google Workspace Automation Engine includes:

- a successful Sheets cleanup run that evaluated 5 input rows, surfaced 3 invalid rows, removed 1 duplicate, produced 2 clean rows, and retained 3 needs-review rows
- a controlled live Gmail-to-Sheets run using the `cloud google acc` that found and fetched one message, parsed it with confidence `1.0` and no parser errors, wrote one `NEW` triage row, recorded a `processed` audit outcome, and applied the configured processing label
- structured logs, workflow artifacts, redacted screenshots, and JSON/CSV audit exports

These are controlled portfolio results, not claims about your data or a production deployment. Your final design will depend on [Google Sheet / Gmail process], Google Workspace permissions, message/data variation, expected volume, and failure-handling requirements.

To define scope, please share:

- a redacted input example
- the required output columns or format
- current duplicate and correction rules
- the Gmail/Sheets actions the automation may perform
- the acceptance criteria for a successful delivery

Once those points are clear, I can recommend a fixed milestone structure or another scope-appropriate engagement. Pricing can be confirmed after scope is agreed.

## 5. Discovery questions

### Current process

- What triggers [current workflow], and how often does it run?
- Who performs the process now, and who reviews the output?
- Which steps are repetitive, error-prone, or hard to verify?
- What must remain a human decision?

### Gmail intake

- Which Gmail account or approved mailbox will the workflow access?
- What query identifies in-scope messages?
- Which fields must be extracted, and how consistent are the message formats?
- What should happen when a required field is missing or ambiguous?
- Which Gmail labels should be applied?
- Should successful or failed items remain in the inbox?
- Are attachments in scope? If so, which types, size limits, and destinations are allowed?

### Google Sheets and cleanup

- What are the input and output tabs?
- Which columns are required, and what formats are valid?
- Which fields define a duplicate?
- Should the first or last duplicate be retained?
- Where should invalid rows and their reasons appear?
- Should the workflow overwrite, clear, append, or upsert output rows?

### Access, security, and operations

- Can an approved test account and test Sheet be used before live access?
- Who will create and retain the Google credentials?
- Which OAuth scopes and resource permissions are allowed?
- Are any fields sensitive and excluded from logs or artifacts?
- How should failures be surfaced and retried?
- Will runs be started manually, or is deployment/scheduling part of the requested scope?

### Delivery and acceptance

- What exact output demonstrates success?
- What sample data can be used for acceptance testing?
- Which documentation and handoff materials are required?
- Is a controlled proof run required before production use?
- What is explicitly out of scope?

## 6. Scope options and package ideas

These are scope patterns, not fixed-price offers. Each can be priced after inputs, access, volume, and acceptance criteria are confirmed.

### Gmail to Sheets intake setup

- map one Gmail query and one target Sheet layout
- configure selected field extraction and message-ID upserts
- configure processing and needs-review labels
- validate against approved test messages
- provide run and verification instructions

### Sheets cleanup and reporting workflow

- map one input schema and normalization rules
- configure required-field and type validation
- define deduplication keys and retention behavior
- create report and needs-review outputs
- validate with a redacted sample dataset

### Google Workspace automation audit

- document the current workflow and bottlenecks
- identify permissions, security, duplicate, and exception risks
- recommend automation boundaries and human review points
- provide a scoped implementation and proof plan

### Proof-backed workflow demo

- configure an approved non-production example
- run a controlled test
- validate agreed outputs and exception paths
- provide redacted screenshots and an evidence summary

### Follow-up delivery package

- update operator documentation after implementation
- run agreed regression and quality checks
- prepare handoff notes, known limitations, and troubleshooting steps
- define optional next-phase work without representing it as delivered

## 7. What to avoid promising

- guaranteed accuracy before representative input formats are reviewed
- zero manual review for inconsistent or ambiguous data
- production readiness based only on a controlled demo
- support for every Gmail message format or spreadsheet schema without configuration
- specific throughput, uptime, revenue, or time savings without measurement
- immediate access to Google accounts or resources before permissions are approved
- fixed delivery scope before inputs, actions, security constraints, and acceptance criteria are known
- deployment or scheduling unless it is explicitly included and designed
- archive, attachment, or alert behavior unless it is configured and tested for that engagement

## 8. Optional closing lines

- If you send a redacted input example and the target output, I can identify the main rules and unknowns before we define scope.
- I can start with a controlled proof against approved test data, then document what is required for live use.
- The first useful step is confirming the field mapping, duplicate rules, exception path, and Google Workspace permissions.
- If the job post reflects the full scope, I can turn it into clear milestones after a short technical discovery.
- I am comfortable keeping uncertain records in a review queue instead of forcing unreliable automation decisions.
- Pricing can be confirmed once the workflow boundaries and acceptance criteria are clear.
