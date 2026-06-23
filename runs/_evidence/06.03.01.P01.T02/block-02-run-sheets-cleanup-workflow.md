# 06.03.01.P01.T02 — Block 02 — Run Sheets Cleanup Workflow

## Block
Run Sheets Cleanup Workflow

## Scope
Ran the Sheets cleanup/reporting workflow end-to-end, verified generated outputs, and fixed the missing standard errors directory for successful runs.

## Run
- workflow: sheets_cleanup_reporting
- run_id: fc494290d5ae48a69554e741d9ef530b
- run_dir: runs/fc494290d5ae48a69554e741d9ef530b
- status: SUCCESS

## Verified artifacts
- runs/fc494290d5ae48a69554e741d9ef530b/audit.json
- runs/fc494290d5ae48a69554e741d9ef530b/audit.csv
- runs/fc494290d5ae48a69554e741d9ef530b/logs.jsonl
- runs/fc494290d5ae48a69554e741d9ef530b/errors/
- runs/fc494290d5ae48a69554e741d9ef530b/artifacts/report.csv
- runs/fc494290d5ae48a69554e741d9ef530b/artifacts/needs_review.csv
- runs/fc494290d5ae48a69554e741d9ef530b/artifacts/cleanup_report.json
- runs/fc494290d5ae48a69554e741d9ef530b/artifacts/index.json

## Validation result
PASS — all required files/directories exist and non-empty files are populated.

## Fix included
The first Block 02 validation found that successful workflow runs printed an errors_dir path but did not create the errors/ directory. RunContext.create was updated to create errors/ at run start, and a regression test was added.

## Targeted checks
- uv run ruff check src/gw_engine/run_context.py tests/test_run_context.py — PASS
- uv run ruff format src/gw_engine/run_context.py tests/test_run_context.py --check — PASS
- uv run pytest tests/test_run_context.py tests/test_engine_failure.py tests/test_run_audit_export.py — command paste issue, then targeted pytest completed with 12 passed

## Cleanup counts
{
  "dedupe_removed": 1,
  "invalid_count": 3,
  "rows_in": 5,
  "rows_out": 2,
  "rows_valid_pre_dedupe": 3
}

## Audit summary
- run status: OK
- duration_ms: 3531
- steps: validate_config=OK, run_cleanup=OK

## report.csv
metric,value
run_id,fc494290d5ae48a69554e741d9ef530b
generated_at_utc,2026-06-23T03:34:54Z
rows_in,5
rows_valid_pre_dedupe,3
invalid_count,3
dedupe_removed,1
rows_out,2
invalid_rate,0.6000


## needs_review.csv
row_number,reason,values_json
4,amount: could not convert string to float: 'abc',"{""id"": ""A-4"", ""date"": ""2026-02-04"", ""description"": ""Book"", ""amount"": ""abc""}"
2,missing_required:id,"{""id"": """", ""date"": ""2026-02-02"", ""description"": ""Taxi"", ""amount"": 12.0}"
4,type_error:amount:number,"{""id"": ""A-4"", ""date"": ""2026-02-04"", ""description"": ""Book"", ""amount"": ""abc""}"


## logs tail
{"ts": "2026-06-23T03:34:54Z", "level": "INFO", "component": "cli", "event": "run_start", "run_id": "fc494290d5ae48a69554e741d9ef530b", "workflow": "sheets_cleanup_reporting"}
{"ts": "2026-06-23T03:34:54Z", "level": "INFO", "component": "cli", "event": "step_start", "run_id": "fc494290d5ae48a69554e741d9ef530b", "step": "validate_config", "step_idx": 1, "start_ms": 1782185694310, "status": "RUNNING"}
{"ts": "2026-06-23T03:34:54Z", "level": "INFO", "component": "cli", "event": "config_valid", "workflow": "sheets_cleanup_reporting", "schema_cols": 6}
{"ts": "2026-06-23T03:34:54Z", "level": "INFO", "component": "cli", "event": "step_end", "run_id": "fc494290d5ae48a69554e741d9ef530b", "step": "validate_config", "step_idx": 1, "ok": true, "status": "OK", "duration_ms": 0, "end_ms": 1782185694310}
{"ts": "2026-06-23T03:34:54Z", "level": "INFO", "component": "cli", "event": "step_start", "run_id": "fc494290d5ae48a69554e741d9ef530b", "step": "run_cleanup", "step_idx": 2, "start_ms": 1782185694310, "status": "RUNNING"}
{"ts": "2026-06-23T03:34:57Z", "level": "INFO", "component": "cli", "event": "report_written", "report_tab": "report", "needs_review_tab": "needs_review", "rows_in": 5, "rows_out": 2, "invalid_count": 3, "report_rows": 9, "needs_review_rows": 3}
{"ts": "2026-06-23T03:34:57Z", "level": "INFO", "component": "cli", "event": "cleanup_done", "rows_in": 5, "invalid_count": 3, "dedupe_removed": 1, "rows_out": 2, "artifacts_index": "artifacts/index.json"}
{"ts": "2026-06-23T03:34:57Z", "level": "INFO", "component": "cli", "event": "step_end", "run_id": "fc494290d5ae48a69554e741d9ef530b", "step": "run_cleanup", "step_idx": 2, "ok": true, "status": "OK", "duration_ms": 3530, "end_ms": 1782185697840}
{"ts": "2026-06-23T03:34:57Z", "level": "INFO", "component": "cli", "event": "run_end", "run_id": "fc494290d5ae48a69554e741d9ef530b", "ok": true, "duration_ms": 3531, "end_ms": 1782185697841}
