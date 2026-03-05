from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from gw_engine.contracts import RunState, Step, StepResult, Workflow
from gw_engine.engine import run_workflow
from gw_engine.gmail_adapter import AttachmentMeta
from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext
from gw_engine.workflows import gmail_to_sheets_intake


def _as_jsonl_lines(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_workflow_attachments_routes_valid_and_quarantines_invalid(
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
        "options": {
            "max_messages": 10,
        },
        "attachments": {
            "enabled": True,
            "max_size_bytes": 1024,
            "allowed_mime_types": ["application/pdf", "text/plain"],
            "allowed_extensions": [".pdf", ".txt"],
            "route_mode": "artifacts",
            "drive_folder_id": "",
        },
    }

    class FakeGmailAdapter:
        def __init__(self, *_, **__) -> None: ...

        def list_message_attachments(self, message_id: str) -> list[AttachmentMeta]:
            assert message_id == "msg-attachments"
            return [
                AttachmentMeta(
                    filename="invoice.pdf",
                    mime_type="application/pdf",
                    size_estimate=5,
                    attachment_id="att-valid",
                    part_id="0.1",
                    message_id=message_id,
                ),
                AttachmentMeta(
                    filename="script.exe",
                    mime_type="application/x-msdownload",
                    size_estimate=6,
                    attachment_id="att-bad",
                    part_id="0.2",
                    message_id=message_id,
                ),
            ]

        def get_attachment_bytes(self, message_id: str, attachment_id: str) -> bytes:
            assert message_id == "msg-attachments"
            if attachment_id == "att-valid":
                return b"pdf-1"
            if attachment_id == "att-bad":
                return b"exe-1"
            raise AssertionError(f"unexpected attachment_id={attachment_id}")

    def fake_build_service(*_, **__) -> Any:
        return object()

    def fake_load_config() -> Any:
        return object()

    def fake_settings_from_env() -> Any:
        return object()

    monkeypatch.setattr(gmail_to_sheets_intake, "GmailAdapter", FakeGmailAdapter)
    monkeypatch.setattr(gmail_to_sheets_intake, "build_service", fake_build_service)
    monkeypatch.setattr(gmail_to_sheets_intake, "load_config", fake_load_config)
    monkeypatch.setattr(gmail_to_sheets_intake, "settings_from_env", fake_settings_from_env)

    workflow_factory = gmail_to_sheets_intake.get_workflow(cfg)
    attachments_step = next(step for step in workflow_factory.steps if step.name == "attachments")

    def seed_state(_ctx: RunContext, state: RunState, _log: JsonlLogger) -> StepResult:
        state.data["message_ids"] = ["msg-attachments"]
        state.data["attachments_enabled"] = True
        state.data["attachments_config"] = cfg["attachments"]
        return StepResult(ok=True, outputs={"message_ids": 1})

    runs_dir = tmp_path / "runs"
    ctx = RunContext.create(runs_dir)
    log = JsonlLogger(path=ctx.logs_path, component="engine")

    result = run_workflow(
        workflow=Workflow(
            name="gmail_to_sheets_intake_attachments",
            steps=[
                Step(name="seed_state", fn=seed_state),
                attachments_step,
            ],
        ),
        ctx=ctx,
        log=log,
    )

    assert result.ok is True

    manifest_path = ctx.run_dir / "attachments" / "manifest.jsonl"
    summary_path = ctx.run_dir / "attachments" / "summary.jsonl"
    raw_dir = ctx.run_dir / "attachments" / "raw"
    quarantine_dir = ctx.run_dir / "attachments" / "quarantine"
    routed_dir = ctx.run_dir / "attachments" / "routed"

    assert manifest_path.exists()
    assert summary_path.exists()

    manifest_rows = _as_jsonl_lines(manifest_path)
    assert len(manifest_rows) == 2
    manifest_by_filename = {row["filename"]: row for row in manifest_rows}
    assert manifest_by_filename["invoice.pdf"]["status"] == "routed_artifacts"
    assert manifest_by_filename["invoice.pdf"]["saved_path"].endswith(
        "attachments/routed/invoice.pdf"
    )
    assert manifest_by_filename["script.exe"]["status"] == "quarantined"
    assert manifest_by_filename["script.exe"]["saved_path"].endswith(
        "attachments/quarantine/script.exe"
    )

    summary_rows = _as_jsonl_lines(summary_path)
    assert len(summary_rows) == 2
    summary_by_filename = {row["filename"]: row for row in summary_rows}
    assert summary_by_filename["invoice.pdf"]["status"] in {"routed_artifacts", "quarantined"}
    assert summary_by_filename["script.exe"]["status"] == "quarantined"

    assert any(p.name == "invoice.pdf" for p in raw_dir.iterdir())
    assert any(p.name == "script.exe" for p in raw_dir.iterdir())
    assert any(p.name == "invoice.pdf" for p in routed_dir.iterdir())
    assert any(p.name == "script.exe" for p in quarantine_dir.iterdir())

    index_payload = json.loads(ctx.artifacts_index_path.read_text(encoding="utf-8"))
    artifact_names = {row["name"] for row in index_payload}
    assert "attachments_manifest_jsonl" in artifact_names
    assert "attachments_summary_jsonl" in artifact_names

    logs = _as_jsonl_lines(ctx.logs_path)
    assert any(event["event"] == "gmail_attachments_summary" for event in logs)
    summary_event = next(event for event in logs if event["event"] == "gmail_attachments_summary")
    assert summary_event["total"] == 2
    assert summary_event["routed"] == 1
    assert summary_event["quarantined"] == 1
    assert summary_event["errors"] == 0
