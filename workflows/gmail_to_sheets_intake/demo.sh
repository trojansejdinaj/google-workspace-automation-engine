#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

WORKFLOW="gmail_to_sheets_intake"
LOCAL_CONFIG="workflows/${WORKFLOW}/config.local.yml"
EXAMPLE_CONFIG="workflows/${WORKFLOW}/config.example.yml"

if [[ -f "$LOCAL_CONFIG" ]]; then
	CONFIG="$LOCAL_CONFIG"
else
	CONFIG="$EXAMPLE_CONFIG"
fi

echo "Using config: ${CONFIG}"
uv run gw run "$WORKFLOW" --config "$CONFIG"
echo "After run: copy 5-10 apply_actions log lines plus artifacts/actions_plan.json and artifacts/actions_applied.json snippets into runs/_evidence/01.04.02.P03.T5-check-proof.txt (redact sensitive values)."
