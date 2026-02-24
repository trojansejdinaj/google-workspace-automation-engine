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
