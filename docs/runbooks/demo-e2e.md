# Demo Runbook (`gw demo`)

This runbook shows how to run the deterministic end-to-end demo and inspect outputs.

## 1) Auth options (high level)

The demo itself does not call external APIs, but normal workflows use one of:
- OAuth user credentials (common for Gmail/dev flows)
- Service account credentials (common for Drive/Sheets automation)

Auth setup and details are documented in:
- `docs/architecture/05-auth.md`

## 2) Run the demo

From the repository root:

```bash
uv run gw demo
```

The command runs a tiny workflow via the engine, writes a small artifact, exports audit files, then prints a final banner including `run_id`, `status`, `run_dir`, and audit paths.

## Run a workflow demo

```bash
./workflows/sheets_cleanup_reporting/demo.sh
# or
uv run gw run sheets_cleanup_reporting --config workflows/sheets_cleanup_reporting/config.example.yml
```

Expected outputs:
- `runs/<run_id>/logs.jsonl`
- `runs/<run_id>/artifacts/report.json`

## 3) Find run artifacts and audit exports

By default runs are stored under `runs/<run_id>/` (or your configured `GW_RUNS_DIR`).

Expected files:
- `runs/<run_id>/logs.jsonl`
- `runs/<run_id>/run.json`
- `runs/<run_id>/steps.json`
- `runs/<run_id>/artifacts/demo_payload.json`
- `runs/<run_id>/audit.json`
- `runs/<run_id>/audit.csv`

Quick inspection:

```bash
ls -la runs/<run_id>
ls -la runs/<run_id>/artifacts
cat runs/<run_id>/run.json
cat runs/<run_id>/steps.json
```
