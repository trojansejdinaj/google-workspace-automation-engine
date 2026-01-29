# Google Workspace Automation Engine

A small engine for running Google Workspace automations with run tracking, structured logs, and an audit trail.

## Setup

```bash
uv sync
```

## Logs
Demo runs write structured logs to:

- `runs/<run_id>/logs.jsonl`

Each line is a JSON object containing `ts`, `level`, `component`, `event`, and `run_id`.
