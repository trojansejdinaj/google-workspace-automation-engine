# 06.03.01.P01.T04 — Block 03 — Upwork Portfolio and Proposal Assets

## Task code

`06.03.01.P01.T04`

## Block name

`Block 03 — Upwork Portfolio and Proposal Assets`

## Status

PASS

## Scope

Created copy/paste-ready Upwork portfolio and proposal assets for the two proven Google Workspace Automation Engine workflows. The sales language is client-readable, includes reusable placeholders and discovery gates, and remains bounded by the controlled evidence stored in the repository.

## Files changed

- `README.md`
- `docs/sales/upwork/README.md`
- `docs/sales/upwork/portfolio-project.md`
- `docs/sales/upwork/proposal-templates.md`
- `runs/_evidence/06.03.01.P01.T04-package-final-qa-sales-assets/block-03-upwork-portfolio-and-proposal-assets.md`

## Sales assets created

- an Upwork asset index with usage instructions, proof links, and claim/security guardrails
- a portfolio project entry covering title, positioning, overview, business problem, solution, both proven workflows, verified results, evidence, technology, comparable client scope, limitations, and screenshot order
- three short proposal templates for Gmail-to-Sheets, spreadsheet cleanup/reporting, and Google Workspace audit jobs
- one detailed proposal template for larger scoped engagements
- discovery questions for process, Gmail, Sheets, access/security, operations, and acceptance criteria
- scope/package ideas without invented prices
- a list of promises to avoid and optional closing lines

## Validation commands run

- Local Markdown link check for the edited README, three Upwork assets, and this proof file: PASS — 68 local links resolved across 5 files
- `git diff --check`: PASS
- `uv run ruff format --check .`: PASS — 61 files already formatted
- `uv run ruff check .`: PASS
- `uv run mypy . --no-incremental`: PASS — no issues found in 61 source files
- `uv run pytest`: PASS — 122 passed, 2 deselected

The two deselected tests are credentialed integration tests excluded by the repository's normal test configuration.

## Workflow code and claim boundaries

No workflow code changed. This block contains only documentation, sales assets, and proof.

All results remain tied to the controlled T02 and T03 proof runs. No fake client names, production deployments, financial results, guarantees, rankings, or time-saved claims were added. No fixed prices were invented.
