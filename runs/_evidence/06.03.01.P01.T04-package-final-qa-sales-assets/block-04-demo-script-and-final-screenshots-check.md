# 06.03.01.P01.T04 — Block 04 — Demo Script and Final Screenshots Check

## Task code

`06.03.01.P01.T04`

## Block name

`Block 04 — Demo Script and Final Screenshots Check`

## Status

PASS WITH DOCUMENTED PLACEHOLDER LIMITATION

## Scope

Created a client/demo-ready presentation script and completed a final file, format, visual, redaction, usage, and reference check for the screenshot assets supporting the README, case study, and Upwork sales materials.

## Files changed

- `README.md`
- `docs/demo/google-workspace-automation-engine-demo-script.md`
- `docs/demo/final-screenshots-check.md`
- `runs/_evidence/06.03.01.P01.T04-package-final-qa-sales-assets/block-04-demo-script-and-final-screenshots-check.md`

## Demo documentation created

- 2-, 5-, and 10-minute presentation paths
- pre-demo safety and setup checklist
- business problem, workflow, proof model, client relevance, and discovery flow
- proof-backed talk tracks for Sheets cleanup and Gmail-to-Sheets intake
- usable screenshot order for client demos and portfolio uploads
- evidence references, claim boundaries, discovery questions, closing script, and follow-up template
- final screenshot inventory with proof purpose, usage, status, dimensions, and redaction notes

## Screenshot inventory result

- T02 Sheets curated evidence: 4 of 4 paths exist; all 4 are valid non-empty PNGs and usable
- T03 Gmail curated evidence: 4 of 4 paths exist; all 4 are valid non-empty PNGs and usable
- Curated screenshots were visually reviewed against the documented proof and redaction expectations
- `docs/assets/` portfolio PNG paths: 8 of 8 paths exist, but all 8 are zero-byte placeholders and are not usable
- The upload and demo order uses only the 8 valid curated evidence screenshots
- No screenshot was generated, replaced, or modified

## Validation commands run

- Local Markdown link check for the edited README, two demo docs, and this proof file: PASS — 102 local links resolved across 4 files
- Screenshot existence, non-empty, signature, and dimension check: PASS — 8 of 8 curated screenshots are valid PNGs
- Portfolio placeholder check: CONFIRMED — all 8 expected `docs/assets/` paths exist and remain zero-byte unusable placeholders
- Visual screenshot review: PASS — curated images match documented proof; controlled Gmail data and sender-address redaction were confirmed
- `git diff --check`: PASS
- `uv run ruff format --check .`: PASS — 61 files already formatted
- `uv run ruff check .`: PASS
- `uv run mypy . --no-incremental`: PASS — no issues found in 61 source files
- `uv run pytest`: PASS — 122 passed, 2 deselected

The two deselected tests are credentialed integration tests excluded by the repository's normal test configuration.

## Workflow code and claim boundaries

No workflow code changed. This block is limited to documentation, demo guidance, screenshot verification, and proof.

No fake screenshots, client names, production usage, revenue or time-saved figures, guarantees, or unsupported results were added. The dedicated non-main account is described only as `cloud google acc`.
