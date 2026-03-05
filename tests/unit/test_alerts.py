from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gw_engine.alerts import build_triage_sheet_url, emit_needs_review_alert
from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext


def _as_jsonl_lines(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_build_triage_sheet_url_appends_gid() -> None:
    assert build_triage_sheet_url("sheet-123", "triage") == (
        "https://docs.google.com/spreadsheets/d/sheet-123/edit#gid=triage"
    )


def test_emit_needs_review_alert_suppressed(tmp_path: Path) -> None:
    ctx = RunContext.create(tmp_path / "runs")
    log = JsonlLogger(path=ctx.logs_path, component="engine")

    payload = emit_needs_review_alert(
        ctx,
        log,
        workflow="gmail_to_sheets_intake",
        sheet_id="sheet-123",
        triage_tab="triage",
        new_count=0,
        total_count=12,
    )

    assert payload["emitted"] is False
    assert payload["new_needs_review_count"] == 0
    assert payload["total_needs_review_count"] == 12
    assert build_triage_sheet_url("sheet-123", "triage") == payload["triage_sheet_url"]

    alert_path = ctx.artifacts_dir / "needs_review_alert.json"
    assert not alert_path.exists()
    assert not ctx.artifacts_index_path.exists()

    logs = _as_jsonl_lines(ctx.logs_path)
    assert logs[-1]["event"] == "needs_review_alert_suppressed"
    assert logs[-1]["new_needs_review_count"] == 0


def test_emit_needs_review_alert_emitted(tmp_path: Path) -> None:
    ctx = RunContext.create(tmp_path / "runs")
    log = JsonlLogger(path=ctx.logs_path, component="engine")

    payload = emit_needs_review_alert(
        ctx,
        log,
        workflow="gmail_to_sheets_intake",
        sheet_id="sheet-123",
        triage_tab="triage",
        new_count=4,
        total_count=10,
    )

    assert payload["emitted"] is True
    assert payload["new_needs_review_count"] == 4
    assert payload["total_needs_review_count"] == 10

    alert_path = ctx.artifacts_dir / "needs_review_alert.json"
    assert alert_path.exists()
    artifact_contents = json.loads(alert_path.read_text(encoding="utf-8"))
    assert artifact_contents["new_needs_review_count"] == 4
    assert artifact_contents["total_needs_review_count"] == 10

    index_payload = json.loads(ctx.artifacts_index_path.read_text(encoding="utf-8"))
    assert len(index_payload) == 1
    assert index_payload[0]["name"] == "needs_review_alert_json"
    assert index_payload[0]["metadata"]["new_needs_review_count"] == 4

    logs = _as_jsonl_lines(ctx.logs_path)
    assert logs[-1]["event"] == "needs_review_alert_emitted"
    assert logs[-1]["new_needs_review_count"] == 4
