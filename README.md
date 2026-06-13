# Google Workspace Automation Engine

A small Python engine for running Google Workspace automations with run tracking, structured logs, typed client construction, retries, and auditable per-run outputs.

## Setup

```bash
uv sync
cp .env.example .env
```

Edit `.env` only with local values. Do not commit credentials, `.env`, `config.local.yml`, or generated `runs/<run_id>/` artifacts.

Authentication and environment details:
- [Google auth](docs/architecture/05-auth.md)
- [Environment loading](docs/architecture/06-env-loading.md)
- [Client factory](docs/architecture/07-client-factory.md)

## Demo

Run the deterministic engine demo. It does not call live Google APIs:

```bash
uv run gw demo
```

Demo runbook:
- [Deterministic demo](docs/runbooks/demo-e2e.md)

## Testing

Unit tests live under `tests/` (including focused unit files like `tests/test_*_unit.py`).

Run the normal local/CI test suite. Integration tests are deselected by default:

```bash
uv run pytest
```

Run a specific unit file:

```bash
uv run pytest tests/test_sheets_validation_unit.py -q
```

Integration tests are marked with `@pytest.mark.integration` and require:

- `GW_TEST_SHEET_ID`
- Auth via either:
	- `GOOGLE_SERVICE_ACCOUNT_JSON`, or
	- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`

Run integration tests locally:

```bash
uv run pytest -m integration
```

## Quality gates

Run the full local quality gate before committing:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy . --no-incremental
uv run pytest
git diff --check
```

## Logs
Demo runs write structured logs to:

- `runs/<run_id>/logs.jsonl`
- `runs/<run_id>/run.json`
- `runs/<run_id>/steps.json`

Each line is a JSON object containing `ts`, `level`, `component`, `event`, and `run_id`.

## Audit export

Export audit data for an existing run:

```bash
gw export <run_id> --format json
gw export <run_id> --format csv
```

Defaults:
- JSON writes `runs/<run_id>/audit.json`
- CSV writes `runs/<run_id>/audit.csv`

## Workflows
- Sheets cleanup (`sheets_cleanup_reporting`): Schema-driven validation (required cols + types) with explicit invalid-row reasons (no silent drops).
- Gmail intake (`gmail_to_sheets_intake`): Gmail search/fetch/parse, Sheets triage upsert, labels/actions, optional attachments, alerts, and audit artifacts.
- Drive intake validator (`drive_intake_validator`): early scaffold/config example; verify implementation status before using for live work.

Workflow docs:
- [Sheets cleanup workflow](workflows/sheets_cleanup_reporting/README.md)
- [Gmail intake workflow](workflows/gmail_to_sheets_intake/README.md)
- [Drive intake validator workflow](workflows/drive_intake_validator/README.md)

Runbooks:
- [Sheets cleanup and reporting](docs/runbooks/sheets-cleanup-reporting.md)
- [Gmail to Sheets intake](docs/runbooks/gmail_to_sheets_intake.md)

## Known limitations

See [known limitations](docs/known-limitations.md).
