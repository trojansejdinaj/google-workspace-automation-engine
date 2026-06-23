# 06.03.01.P01.T02 — Block 03 — Validate Sheets Outputs

## Block
Validate Sheets Outputs

## Scope
Inspected the generated report and needs-review outputs. Verified row counts, invalid rows, cleanup metrics, audit fields, and business story clarity.

## Source run
- run_id: fc494290d5ae48a69554e741d9ef530b
- run_dir: runs/fc494290d5ae48a69554e741d9ef530b

## Validated files
- runs/fc494290d5ae48a69554e741d9ef530b/artifacts/report.csv
- runs/fc494290d5ae48a69554e741d9ef530b/artifacts/needs_review.csv
- runs/fc494290d5ae48a69554e741d9ef530b/artifacts/cleanup_report.json
- runs/fc494290d5ae48a69554e741d9ef530b/audit.json
- runs/fc494290d5ae48a69554e741d9ef530b/logs.jsonl

## Validation summary
- rows_in: 5
- rows_valid_pre_dedupe: 3
- invalid_count: 3
- dedupe_removed: 1
- rows_out: 2
- invalid_rate: 0.6000
- needs_review rows: 3
- audit run status: OK
- audit steps: validate_config=OK, run_cleanup=OK

## Business story
The workflow reads 5 raw rows, catches 3 review issues, removes 1 duplicate, and produces 2 clean output rows. The report explains the cleanup funnel with rows_in, invalid_count, dedupe_removed, rows_out, and invalid_rate. The needs-review file gives specific row-level reasons so an operator can fix the bad input rows.

## Captured validation output

RUN_ID: fc494290d5ae48a69554e741d9ef530b
Report metrics: {'run_id': 'fc494290d5ae48a69554e741d9ef530b', 'generated_at_utc': '2026-06-23T03:34:54Z', 'rows_in': '5', 'rows_valid_pre_dedupe': '3', 'invalid_count': '3', 'dedupe_removed': '1', 'rows_out': '2', 'invalid_rate': '0.6000'}
Needs-review rows: 3
Needs-review reasons: ["amount: could not convert string to float: 'abc'", 'missing_required:id', 'type_error:amount:number']
Cleanup counts: {'dedupe_removed': 1, 'invalid_count': 3, 'rows_in': 5, 'rows_out': 2, 'rows_valid_pre_dedupe': 3}
Audit status: OK
Audit steps: {'validate_config': 'OK', 'run_cleanup': 'OK'}
Business story: The workflow reads 5 raw rows, catches 3 review issues, removes 1 duplicate, and produces 2 clean output rows. The report explains the cleanup funnel with rows_in, invalid_count, dedupe_removed, rows_out, and invalid_rate. The needs-review file gives specific row-level reasons so an operator can fix the bad input rows.
Block 03 output validation: PASS
