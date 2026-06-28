# Google Workspace Automation Engine Demo Script

## Purpose

Use this script to present the Google Workspace Automation Engine during a client call, Loom recording, Upwork portfolio walkthrough, or sales conversation. It keeps the presentation focused on business problems, operator-visible outputs, and repository-backed proof.

The demo covers two proven workflows:

- Google Sheets cleanup and reporting
- Gmail-to-Sheets intake and triage

The results shown are controlled portfolio evidence, not client or production performance claims.

## Best use cases

- a quick portfolio explanation for an Upwork lead
- a discovery call with a team that copies Gmail data into Sheets
- a spreadsheet cleanup or reporting conversation
- a technical review where logs, audit exports, and exception handling matter
- a recorded walkthrough attached to a proposal or follow-up message

## Demo length options

| Length | Best for | What to show |
| --- | --- | --- |
| 2 minutes | Initial pitch or proposal attachment | Business problem, one Sheets output, one Gmail output, evidence model, discovery question |
| 5 minutes | Portfolio or sales walkthrough | Both workflows, verified results, human-review paths, Gmail label, and audit evidence |
| 10 minutes | Technical proof discussion | Full five-minute flow plus proof files, artifact model, limitations, security, and client-specific scope questions |

### 2-minute quick pitch

- **0:00–0:20:** State the manual Gmail and Sheets problem.
- **0:20–0:50:** Show the Sheets report and needs-review screenshots.
- **0:50–1:20:** Show the Gmail-to-Sheets triage row and processing label.
- **1:20–1:45:** Explain logs, audit exports, and curated evidence.
- **1:45–2:00:** Ask which current process the client wants to make repeatable.

### 5-minute portfolio walkthrough

- **0:00–0:40:** Open the [project README](../../README.md) and explain the two workflow outcomes.
- **0:40–2:00:** Walk through Sheets cleanup metrics, needs-review handling, and proof.
- **2:00–3:20:** Walk through Gmail intake, the triage row, processing label, and proof.
- **3:20–4:10:** Show how logs, artifacts, and audit exports make runs reviewable.
- **4:10–4:40:** Connect the workflows to the prospect's process without claiming a fit before discovery.
- **4:40–5:00:** Close with one discovery question and a concrete next step.

### 10-minute technical proof walkthrough

Use the five-minute flow, then add:

- the [full case study](../case-studies/google-workspace-automation-engine.md)
- the [Sheets proof file](../../runs/_evidence/06.03.01.P01.T02/proof.md)
- the [Gmail-to-Sheets proof file](../../runs/_evidence/06.03.01.P01.T03/proof.md)
- artifact screenshots showing reports, triage data, logs, and audit outputs
- the distinction between generated operational runs and curated redacted evidence
- credential, permission, integration-test, deployment, and scheduling limitations
- discovery questions about schemas, message variation, duplicate rules, human review, and acceptance criteria

## Pre-demo checklist

- [ ] Choose the 2-, 5-, or 10-minute version before the call.
- [ ] Open the [README](../../README.md), [case study](../case-studies/google-workspace-automation-engine.md), and relevant proof files in separate tabs.
- [ ] Open only the valid screenshots listed in the [final screenshot check](final-screenshots-check.md).
- [ ] Do not use the zero-byte placeholder images under `docs/assets/`.
- [ ] Confirm the browser or editor is zoomed so metrics and labels are readable.
- [ ] Close terminals or tabs that show local configuration, credentials, private identifiers, or unrelated work.
- [ ] Do not open `.env`, `config.local.yml`, OAuth files, refresh tokens, or generated operational run folders during screen sharing.
- [ ] Use `cloud google acc` when referring to the dedicated non-main Google account.
- [ ] Keep the [Upwork portfolio entry](../sales/upwork/portfolio-project.md) and [proposal templates](../sales/upwork/proposal-templates.md) available for the client-relevance section.
- [ ] Prepare one discovery question based on the prospect's stated workflow.

## Demo flow

### 1. Open the README or case study

Show the two-row workflow summary in the [README](../../README.md) or the solution overview in the [case study](../case-studies/google-workspace-automation-engine.md).

Say:

> This project addresses two common operations problems: inconsistent spreadsheet data and manual transfer of inbox requests into a shared tracking queue. The important part is not only moving data; each workflow keeps exceptions visible and produces evidence that shows what the run did.

### 2. Explain the business problem

Say:

> Teams often use Gmail and Google Sheets as an informal operating system. Manual copy/paste and cleanup can create missing fields, duplicate records, missed follow-up, and no reliable audit trail. These workflows make the rules repeatable while leaving uncertain records available for human review.

Do not claim that every Gmail or Sheets process can use the workflows unchanged. Client schemas, message formats, permissions, and exception rules require discovery.

### 3. Show the Sheets cleanup workflow

Open these screenshots in order:

1. [Report tab](../../runs/_evidence/06.03.01.P01.T02/screenshots/02-report-tab.png)
2. [Needs-review tab](../../runs/_evidence/06.03.01.P01.T02/screenshots/03-needs-review-tab.png)
3. [Terminal success banner](../../runs/_evidence/06.03.01.P01.T02/screenshots/01-terminal-success-banner.png)
4. [Artifact view](../../runs/_evidence/06.03.01.P01.T02/screenshots/04-artifact-view.png)

Use the Sheets talk track below. Lead with the report and exception queue; use terminal and artifact views as supporting proof.

### 4. Show the Gmail-to-Sheets intake workflow

Open these screenshots in order:

1. [Redacted Sheets triage row](../../runs/_evidence/06.03.01.P01.T03/screenshots/02-sheets-triage-row-redacted.png)
2. [Redacted Gmail message and processing label](../../runs/_evidence/06.03.01.P01.T03/screenshots/03-gmail-test-message-label-redacted.png)
3. [Terminal validation pass](../../runs/_evidence/06.03.01.P01.T03/screenshots/01-terminal-validation-pass.png)
4. [Run artifacts](../../runs/_evidence/06.03.01.P01.T03/screenshots/04-run-artifacts-folder.png)

Use the Gmail talk track below. Make clear that the screenshot shows controlled test data and the live proof used the `cloud google acc`.

### 5. Show the proof and evidence model

Open the [Sheets proof](../../runs/_evidence/06.03.01.P01.T02/proof.md) and [Gmail proof](../../runs/_evidence/06.03.01.P01.T03/proof.md).

Say:

> Each run receives an ID and writes structured logs, step records, errors, and workflow-specific artifacts. Step-level audits can be exported as JSON and CSV. Generated run folders stay out of version control because they can contain environment-specific data; curated, reviewed proof is stored separately under `runs/_evidence/`.

### 6. Show sales and client relevance

Use the [Upwork portfolio entry](../sales/upwork/portfolio-project.md) to connect the proof to relevant use cases: lead or service-request intake, invoice or order capture, CRM import preparation, reporting input validation, and spreadsheet exception handling.

Say:

> A similar engagement would start by mapping your fields, actions, duplicate rules, review cases, permissions, and acceptance criteria. The workflow would then be configured or adapted against approved test data before any live use.

### 7. Close with a discovery question

Choose one:

- Which part of your current Gmail or Sheets process creates the most manual correction work?
- What exact output would make this workflow successful for your team?
- When the automation is uncertain, what should go to human review rather than being changed automatically?
- Which duplicate or rerun problem matters most in your current process?

## Talk track — Sheets cleanup and reporting

> This workflow reads Sheet rows, normalizes configured strings, dates, and numbers, validates required fields and data types, and deduplicates validated records. It does not silently discard invalid input; those issues are written to a needs-review output with specific reasons.

While showing the report tab:

> In the controlled proven run, five input rows were evaluated. Three invalid issues were surfaced, one duplicate was removed, and two clean rows were produced. The report records that cleanup funnel directly.

While showing the needs-review tab:

> The operator can see the source row, the rejection reason, and the original values. That makes correction work explicit instead of hiding it inside a script failure or dropping the row.

While showing terminal and artifacts:

> Run `fc494290d5ae48a69554e741d9ef530b` completed with workflow status `SUCCESS`. Its audit recorded `validate_config=OK` and `run_cleanup=OK`, and the run produced report, needs-review, log, JSON audit, and CSV audit evidence.

## Talk track — Gmail to Sheets intake

> This workflow searches Gmail with a configured query, fetches matching messages, extracts selected fields, records parser confidence and errors, and upserts a triage row by Gmail message ID. It then applies the configured Gmail label and writes action and audit evidence.

While showing the triage row:

> The live controlled proof used the `cloud google acc`, one controlled Gmail test message, and a real Google Sheets triage tab. One message was found and fetched. It produced one triage row with status `NEW`; parser confidence was `1.0` and parser errors were empty.

While showing the Gmail label:

> The per-message audit recorded outcome `processed`, and the applied action included `label:gw/processed`. The sender address is redacted in the portfolio evidence, and the visible field values are controlled test data.

While showing validation and artifacts:

> Run `2c522287aa004b389d8fb49daa2ba164` completed with status `OK`. The run produced parsed data, a triage export, a triage audit, planned and applied action records, structured logs, and JSON/CSV audit exports.

## Screenshot order for a clean demo

Use business-facing outputs first, then technical evidence:

1. [Sheets report tab](../../runs/_evidence/06.03.01.P01.T02/screenshots/02-report-tab.png)
2. [Sheets needs-review tab](../../runs/_evidence/06.03.01.P01.T02/screenshots/03-needs-review-tab.png)
3. [Redacted Gmail-to-Sheets triage row](../../runs/_evidence/06.03.01.P01.T03/screenshots/02-sheets-triage-row-redacted.png)
4. [Redacted Gmail processing label](../../runs/_evidence/06.03.01.P01.T03/screenshots/03-gmail-test-message-label-redacted.png)
5. [Sheets terminal success](../../runs/_evidence/06.03.01.P01.T02/screenshots/01-terminal-success-banner.png)
6. [Gmail terminal validation](../../runs/_evidence/06.03.01.P01.T03/screenshots/01-terminal-validation-pass.png)
7. [Sheets artifact view](../../runs/_evidence/06.03.01.P01.T02/screenshots/04-artifact-view.png)
8. [Gmail run artifacts](../../runs/_evidence/06.03.01.P01.T03/screenshots/04-run-artifacts-folder.png)

For a two-minute demo, use items 1, 2, 3, and 4. For a five-minute demo, add items 5 and 8. Use all eight only when the audience wants technical proof.

## Evidence to show

- [Sheets final proof](../../runs/_evidence/06.03.01.P01.T02/proof.md) for the exact run ID, status, outputs, and cleanup metrics
- [Gmail final proof](../../runs/_evidence/06.03.01.P01.T03/proof.md) for the live controlled run, parsed row, triage result, Gmail action, and audit exports
- [Case study](../case-studies/google-workspace-automation-engine.md) for the full problem-solution-proof narrative
- [Final screenshot check](final-screenshots-check.md) for current validity, redaction notes, placeholder status, and upload order
- [Upwork portfolio entry](../sales/upwork/portfolio-project.md) for concise client-facing positioning

If the discussion becomes technical, explain the run contract and artifact names. Do not open unreviewed generated run folders or local configuration during a client-facing screen share.

## What not to claim

- client deployments, client names, or production usage
- revenue impact or measured time savings
- guaranteed parsing or validation accuracy
- production scale, throughput, uptime, or load-test results
- zero need for human review
- support for every Gmail format or Sheets schema without adaptation
- deployment or scheduling that is not currently documented
- archive, attachment, or alert behavior as part of the successful one-message proof
- the zero-byte `docs/assets/` placeholder PNGs as usable screenshots
- any outcome not present in the README, case study, or T02/T03 proof files

## Client discovery questions

- What starts the current workflow, and who owns the output?
- Which Gmail messages or Sheet rows are in scope?
- What fields are required, and what formats are considered valid?
- What defines a duplicate, and which record should be retained?
- What should happen when a field is missing or ambiguous?
- Which changes may the automation make in Gmail or Sheets?
- Which cases must remain a human decision?
- What credentials, OAuth scopes, and resource permissions are approved?
- Can approved test messages and a test Sheet be used for validation?
- What output and evidence will count as acceptance?
- Is manual execution sufficient, or is deployment and scheduling a separate requirement?

## Short closing script

> The proof here shows that both workflows can produce structured outputs, preserve review cases, and record what each run did. The next step would be to map your actual fields, actions, permissions, duplicate rules, and acceptance criteria. If you share a redacted example of the current input and desired output, I can identify the main implementation decisions and propose a bounded scope.

## Follow-up message template after the demo

Hi [client name],

Thanks for walking through [current workflow] with me.

Based on the discussion, the main goal is to turn [current input/process] into [desired output] while keeping [exceptions or human-review cases] visible. The relevant portfolio proof is the [Sheets cleanup / Gmail-to-Sheets] workflow, which demonstrates structured outputs, review handling, and per-run audit evidence in a controlled environment.

Before I define implementation scope, I need to confirm:

- [field or message format question]
- [duplicate/rerun question]
- [Gmail or Sheets action question]
- [permission/security question]
- [acceptance criterion]

If you send a redacted input example and the expected output layout, I can turn those points into a delivery plan. Pricing can be confirmed after the workflow boundaries and access requirements are agreed.

Regards,

[your name]
