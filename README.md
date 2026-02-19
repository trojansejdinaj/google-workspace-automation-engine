# Google Workspace Automation Engine

A small engine for running Google Workspace automations with run tracking, structured logs, and an audit trail.

## Setup

```bash
uv sync
```

## Testing

Unit tests live under `tests/` (including focused unit files like `tests/test_*_unit.py`).

Run unit tests locally (integration excluded by default):

```bash
uv run pytest -m "not integration"
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

CI expectation: integration tests are excluded by default. The CI workflow runs:

```bash
uv run pytest -m "not integration"
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

## Demo

Run the deterministic end-to-end demo:

```bash
uv run gw demo
```

Runbook:
- `docs/runbooks/demo-e2e.md`

## Workflows
- Sheets cleanup (`sheets_cleanup_reporting`): Schema-driven validation (required cols + types) with explicit invalid-row reasons (no silent drops).
