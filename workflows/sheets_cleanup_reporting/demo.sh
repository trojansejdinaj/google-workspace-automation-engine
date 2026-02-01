#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

WORKFLOW="sheets_cleanup_reporting"
CONFIG="workflows/${WORKFLOW}/config.example.yml"

uv run python -m gw_engine.cli run "$WORKFLOW" --config "$CONFIG"
