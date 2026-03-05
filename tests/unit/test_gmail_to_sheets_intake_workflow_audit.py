from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from gw_engine.contracts import RunState, Step, StepResult, Workflow
from gw_engine.engine import run_workflow
from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext
from gw_engine.workflows import gmail_to_sheets_intake


def _as_jsonl_lines(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_apply_actions_writes_audit_rows_with_outcomes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg: dict[str, Any] = {
        "gmail": {
            "gmail_query": "in:inbox",
            "labels": {
                "success": "gw/processed",
                "needs_review": "gw/needs-review",
                "error": "gw/error",
            },
        },
        "sheets": {
            "sheet_id": "DUMMY",
            "tabs": {"triage_tab": "triage"},
            "defaults": {"status": "NEW"},
        },
        "options": {"min_confidence": 0.6},
    }

    class FakeGmailAdapter:
        def __init__(self, *_, **__) -> None:
            self.labels: dict[str, str] = {}
            self.calls: list[tuple[list[str], list[str], list[str]]] = []

        def ensure_label(self, name: str) -> str:
            label_id = f"label-{name}"
            self.labels[name] = label_id
            return label_id

        def batch_modify(
            self,
            *,
            message_ids: list[str],
            add_label_ids: list[str],
            remove_label_ids: list[str],
        ) -> None:
            self.calls.append((list(message_ids), list(add_label_ids), list(remove_label_ids)))

    adapter = FakeGmailAdapter()

    def fake_build_service(*_, **__) -> Any:
        return object()

    def fake_load_config() -> Any:
        return object()

    def fake_settings_from_env() -> Any:
        return object()

    monkeypatch.setattr(gmail_to_sheets_intake, "GmailAdapter", lambda *_, **__: adapter)
    monkeypatch.setattr(gmail_to_sheets_intake, "build_service", fake_build_service)
    monkeypatch.setattr(gmail_to_sheets_intake, "load_config", fake_load_config)
    monkeypatch.setattr(gmail_to_sheets_intake, "settings_from_env", fake_settings_from_env)

    workflow_factory = gmail_to_sheets_intake.get_workflow(cfg)
    apply_actions_step = next(
        step for step in workflow_factory.steps if step.name == "apply_actions"
    )

    def seed_state(_ctx: RunContext, state: RunState, _log: JsonlLogger) -> StepResult:
        state.data["action_items"] = [
            {
                "message_id": "msg-processed",
                "parse_ok": True,
                "error_count": 0,
                "confidence": 0.92,
            },
            {
                "message_id": "msg-review",
                "parse_ok": True,
                "error_count": 1,
                "confidence": 0.28,
            },
            {"message_id": "", "parse_ok": True, "error_count": 0, "confidence": 0.99},
        ]
        state.data["action_parse_error_map"] = {"msg-review": ["missing_field:invoice_or_order_id"]}
        state.data["triage_message_row_map"] = {"msg-processed": 12, "msg-review": 13}
        state.data["gmail_min_confidence"] = 0.6
        state.data["gmail_success_label_name"] = "gw/processed"
        state.data["gmail_needs_review_label_name"] = "gw/needs-review"
        state.data["gmail_error_label_name"] = "gw/error"
        state.data["gmail_archive_on_success"] = False
        state.data["gmail_archive_on_failure"] = False
        return StepResult(ok=True)

    ctx = RunContext.create(tmp_path / "runs")
    log = JsonlLogger(path=ctx.logs_path, component="engine")

    result = run_workflow(
        workflow=Workflow(
            name="gmail_to_sheets_intake_audit",
            steps=[
                Step(name="seed_state", fn=seed_state),
                apply_actions_step,
            ],
        ),
        ctx=ctx,
        log=log,
    )

    assert result.ok is True
    assert adapter.calls
    assert adapter.calls[0][0] == ["msg-processed"]
    assert adapter.calls[0][1] == ["label-gw/processed"]
    assert adapter.calls[1][0] == ["msg-review"]
    assert adapter.calls[1][1] == ["label-gw/needs-review"]

    artifact_rows = _as_jsonl_lines(ctx.artifacts_dir / "triage_audit.jsonl")
    rows = {row["message_id"]: row for row in artifact_rows}

    assert rows["msg-processed"]["outcome"] == "processed"
    assert rows["msg-processed"]["sheet_row_id"] == 12
    assert rows["msg-processed"]["gmail_actions"] == ["label:gw/processed"]
    assert rows["msg-review"]["outcome"] == "needs_review"
    assert rows["msg-review"]["reason"] == "needs_review:missing_field:invoice_or_order_id"
    assert rows["msg-review"]["gmail_actions"] == ["label:gw/needs-review"]
    assert rows[""]["outcome"] == "skipped"
    assert rows[""]["reason"] == "missing_message_id"

    index_payload = json.loads(ctx.artifacts_index_path.read_text(encoding="utf-8"))
    assert any(row["name"] == "triage_audit_jsonl" for row in index_payload)
    assert any(event["event"] == "triage_audit_written" for event in _as_jsonl_lines(ctx.logs_path))
