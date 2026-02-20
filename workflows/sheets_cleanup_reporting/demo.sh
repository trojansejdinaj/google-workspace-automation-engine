#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

WORKFLOW="sheets_cleanup_reporting"
LOCAL_CONFIG="workflows/${WORKFLOW}/config.local.yml"
EXAMPLE_CONFIG="workflows/${WORKFLOW}/config.example.yml"

if [[ -f "$LOCAL_CONFIG" ]]; then
	CONFIG="$LOCAL_CONFIG"
else
	CONFIG="$EXAMPLE_CONFIG"
fi

echo "Using config: ${CONFIG}"

# Preflight: resolve/inject sheet_id (loader does not expand ${VAR} automatically),
# and ensure sheets.sheet_id is configured for local execution.
tmp_cfg="$(mktemp -t gw_sheets_cleanup_cfg.XXXXXX.yml)"
if ! python - "$CONFIG" "$tmp_cfg" <<'PY'
import os
import sys
from pathlib import Path

try:
	import yaml
except Exception:
	print("Preflight failed: PyYAML is required to validate config.")
	sys.exit(2)

cfg_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

if not isinstance(cfg, dict):
	print("Preflight failed: config root must be a mapping.")
	sys.exit(2)

sheets = cfg.get("sheets") or {}
if not isinstance(sheets, dict):
	sheets = {}

raw_sheet_id = sheets.get("sheet_id")

sheet_id = raw_sheet_id
if isinstance(raw_sheet_id, str):
	sheet_id = raw_sheet_id.strip()

if sheet_id == "${GW_SA_TEST_SHEET_ID}":
	env_sheet_id = (os.getenv("GW_SA_TEST_SHEET_ID") or "").strip()
	if not env_sheet_id:
		print("Preflight failed: GW_SA_TEST_SHEET_ID is not set.")
		print("Set GW_SA_TEST_SHEET_ID in your shell, or put a real sheets.sheet_id in config.local.yml.")
		sys.exit(2)
	sheet_id = env_sheet_id

invalid_values = {"<REPLACE_ME>", "DUMMY_SHEET_ID", "", None}
if sheet_id in invalid_values:
	print("Preflight failed: sheets.sheet_id is not configured.")
	print("Set workflows/sheets_cleanup_reporting/config.local.yml -> sheets.sheet_id to a real spreadsheet ID,")
	print("or set sheets.sheet_id to ${GW_SA_TEST_SHEET_ID} and export GW_SA_TEST_SHEET_ID.")
	sys.exit(2)

sheets["sheet_id"] = sheet_id
cfg["sheets"] = sheets
out_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
PY
then
	rm -f "$tmp_cfg"
	exit 2
fi

CONFIG="$tmp_cfg"
echo "Using resolved config: ${CONFIG}"

# Uses the console script defined in pyproject.toml ([project.scripts] gw=...)
# 1) Run workflow and capture stdout for robust post-processing.
tmp_out="$(mktemp -t gw_sheets_cleanup_demo.XXXXXX.out)"
trap 'rm -f "$tmp_out" "$tmp_cfg"' EXIT

echo "Running workflow: ${WORKFLOW}"
set +e
uv run gw run "$WORKFLOW" --config "$CONFIG" | tee "$tmp_out"
RUN_EXIT=${PIPESTATUS[0]}
set -e

# 2/3) Parse the LAST JSON object from stdout, then extract run_id + ok/status.
#    (stdout may include non-JSON lines)
if ! parse_out="$(python - "$tmp_out" <<'PY'
import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8", errors="replace")

# Find candidate JSON-like blocks and parse from the end.
candidates = re.findall(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, flags=re.DOTALL)
obj = None
for raw in reversed(candidates):
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            break
        obj = None
    except Exception:
        continue

if obj is None:
    print("JSON_PARSE_ERROR")
    sys.exit(2)

run_id = str(obj.get("run_id") or "").strip()
status = str(obj.get("status") or "").strip()
ok = obj.get("ok")

if not run_id:
    print("MISSING_RUN_ID")
    sys.exit(3)

print(run_id)
print(status)
print(ok)
PY
)"; then
	echo "=== GW WORKFLOW DEMO FAILURE ==="
	echo "workflow=${WORKFLOW}"
	echo "command_exit_code=${RUN_EXIT}"
	echo "error=Failed to parse run metadata from stdout"
	echo "==============================="
	exit 1
fi

run_id="$(printf "%s\n" "$parse_out" | sed -n '1p')"
status="$(printf "%s\n" "$parse_out" | sed -n '2p')"
ok_raw="$(printf "%s\n" "$parse_out" | sed -n '3p')"

if [[ -z "$run_id" ]]; then
	echo "=== GW WORKFLOW DEMO FAILURE ==="
	echo "workflow=${WORKFLOW}"
	echo "command_exit_code=${RUN_EXIT}"
	echo "error=Missing run_id in parsed output"
	echo "==============================="
	exit 1
fi

# 4/5) Always export audit files if run_id exists, even when RUN_EXIT != 0.
set +e
uv run gw export "$run_id" --format json >/dev/null
EXPORT_JSON_EXIT=$?
uv run gw export "$run_id" --format csv >/dev/null
EXPORT_CSV_EXIT=$?
set -e

run_dir="runs/${run_id}"
audit_json="${run_dir}/audit.json"
audit_csv="${run_dir}/audit.csv"
logs_path="${run_dir}/logs.jsonl"
errors_dir="${run_dir}/errors"

# Derive human-friendly status for end banner.
if [[ $RUN_EXIT -eq 0 && ( "$ok_raw" == "True" || "$ok_raw" == "true" ) ]]; then
	banner_status="SUCCESS"
else
	banner_status="FAILED"
fi

# duration_ms: prefer stdout JSON if present, else fallback to run summary file.
duration_ms="$(python - "$tmp_out" "$run_dir/run.json" <<'PY'
import json
import re
import sys
from pathlib import Path

out_path = Path(sys.argv[1])
run_json_path = Path(sys.argv[2])

def as_duration(value):
	if isinstance(value, int):
		return str(value)
	return ""

text = out_path.read_text(encoding="utf-8", errors="replace")
candidates = re.findall(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, flags=re.DOTALL)

duration = ""
for raw in reversed(candidates):
	try:
		obj = json.loads(raw)
	except Exception:
		continue
	if isinstance(obj, dict):
		duration = as_duration(obj.get("duration_ms"))
		if duration:
			break

if not duration and run_json_path.exists():
	try:
		run_obj = json.loads(run_json_path.read_text(encoding="utf-8"))
		if isinstance(run_obj, dict):
			duration = as_duration(run_obj.get("duration_ms"))
	except Exception:
		pass

print(duration)
PY
)"

# 6) Verify both expected artifacts exist after export.
if [[ $EXPORT_JSON_EXIT -ne 0 || $EXPORT_CSV_EXIT -ne 0 || ! -f "$audit_json" || ! -f "$audit_csv" ]]; then
	echo "=== GW WORKFLOW DEMO FAILURE ==="
	echo "workflow=${WORKFLOW}"
	echo "run_id=${run_id}"
	echo "status=${status:-unknown}"
	echo "ok=${ok_raw:-unknown}"
	echo "command_exit_code=${RUN_EXIT}"
	echo "error=Audit export failed or required files are missing"
	echo "export_json_exit=${EXPORT_JSON_EXIT}"
	echo "export_csv_exit=${EXPORT_CSV_EXIT}"
	echo "expected_json=${audit_json}"
	echo "expected_csv=${audit_csv}"
	echo "logs=${logs_path}"
	echo "errors_dir=${errors_dir}"
	echo "==============================="
	exit 1
fi

# 6/7) End banner includes run metadata and export paths.
echo "=== GW WORKFLOW DEMO END ==="
echo "workflow=${WORKFLOW}"
echo "run_id=${run_id}"
echo "status=${banner_status}"
echo "ok=${ok_raw:-unknown}"
echo "command_exit_code=${RUN_EXIT}"
echo "run_dir=${run_dir}"
if [[ -n "$duration_ms" ]]; then
	echo "duration_ms=${duration_ms}"
fi
echo "audit_json=${audit_json}"
echo "audit_csv=${audit_csv}"
echo "logs=${logs_path}"
echo "errors_dir=${errors_dir}"
echo "==============================="

# 7) Final exit code mirrors workflow command exit code after successful export checks.
if [[ $RUN_EXIT -eq 0 ]]; then
	exit 0
fi
exit "$RUN_EXIT"
