# Google Workspace Automation Engine

A small engine for running Google Workspace automations with run tracking, structured logs, and an audit trail.

## Setup

```bash
uv sync
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
