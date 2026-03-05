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


def _base_config() -> dict[str, Any]:
    return {
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
    }


def test_emit_alert_step_emits_when_new_needs_review_count_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _base_config()
    cfg["alerts"] = {"enabled": True, "include_total_count": True}

    search_calls: list[tuple[str, int]] = []

    class FakeGmailAdapter:
        def __init__(self, *_, **__) -> None: ...

        def search_message_ids(self, query: str, max_results: int = 50) -> list[str]:
            search_calls.append((query, max_results))
            return ["m-1", "m-2", "m-3", "m-4"]

    monkeypatch.setattr(gmail_to_sheets_intake, "GmailAdapter", FakeGmailAdapter)
    monkeypatch.setattr(gmail_to_sheets_intake, "build_service", lambda *_, **__: object())
    monkeypatch.setattr(gmail_to_sheets_intake, "load_config", lambda: object())
    monkeypatch.setattr(gmail_to_sheets_intake, "settings_from_env", lambda: object())

    workflow = gmail_to_sheets_intake.get_workflow(cfg)
    alert_step = next(step for step in workflow.steps if step.name == "emit_alert_if_needs_review")

    def seed_state(_ctx: RunContext, state: RunState, _log: JsonlLogger) -> StepResult:
        state.data["needs_review_new_count"] = 4
        state.data["gmail_needs_review_label_name"] = "gw/needs-review"
        return StepResult(ok=True, outputs={"needs_review_new_count": 4})

    ctx = RunContext.create(tmp_path / "runs")
    log = JsonlLogger(path=ctx.logs_path, component="engine")
    result = run_workflow(
        workflow=Workflow(
            name="gmail_to_sheets_intake_alerts",
            steps=[Step(name="seed_state", fn=seed_state), alert_step],
        ),
        ctx=ctx,
        log=log,
    )

    assert result.ok is True
    assert search_calls == [("label:gw/needs-review", 500)]

    logs = _as_jsonl_lines(ctx.logs_path)
    emitted = next(event for event in logs if event["event"] == "needs_review_alert_emitted")
    assert emitted["workflow"] == "gmail_to_sheets_intake"
    assert emitted["new_needs_review_count"] == 4
    assert emitted["total_needs_review_count"] == 4

    index_payload = json.loads(ctx.artifacts_index_path.read_text(encoding="utf-8"))
    assert any(row["name"] == "needs_review_alert_json" for row in index_payload)


def test_emit_alert_step_suppresses_when_no_new_needs_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _base_config()
    cfg["alerts"] = {"enabled": True, "include_total_count": False}

    monkeypatch.setattr(gmail_to_sheets_intake, "build_service", lambda *_, **__: object())
    monkeypatch.setattr(gmail_to_sheets_intake, "load_config", lambda: object())
    monkeypatch.setattr(gmail_to_sheets_intake, "settings_from_env", lambda: object())

    workflow = gmail_to_sheets_intake.get_workflow(cfg)
    alert_step = next(step for step in workflow.steps if step.name == "emit_alert_if_needs_review")

    def seed_state(_ctx: RunContext, state: RunState, _log: JsonlLogger) -> StepResult:
        state.data["needs_review_new_count"] = 0
        state.data["gmail_needs_review_label_name"] = "gw/needs-review"
        return StepResult(ok=True, outputs={"needs_review_new_count": 0})

    ctx = RunContext.create(tmp_path / "runs")
    log = JsonlLogger(path=ctx.logs_path, component="engine")
    result = run_workflow(
        workflow=Workflow(
            name="gmail_to_sheets_intake_alerts",
            steps=[Step(name="seed_state", fn=seed_state), alert_step],
        ),
        ctx=ctx,
        log=log,
    )

    assert result.ok is True

    logs = _as_jsonl_lines(ctx.logs_path)
    suppressed = next(event for event in logs if event["event"] == "needs_review_alert_suppressed")
    assert suppressed["new_needs_review_count"] == 0
    assert not ctx.artifacts_dir.joinpath("needs_review_alert.json").exists()


def test_alert_step_disabled_skips_alerting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _base_config()
    cfg["alerts"] = {"enabled": False, "include_total_count": True}

    called = False

    class FailingGmailAdapter:
        def __init__(self, *_, **__) -> None:
            nonlocal called
            called = True

        def search_message_ids(self, query: str, max_results: int = 50) -> list[str]:
            raise AssertionError("search should not be called when alerts are disabled")

    monkeypatch.setattr(gmail_to_sheets_intake, "GmailAdapter", FailingGmailAdapter)
    monkeypatch.setattr(gmail_to_sheets_intake, "build_service", lambda *_, **__: object())
    monkeypatch.setattr(gmail_to_sheets_intake, "load_config", lambda: object())
    monkeypatch.setattr(gmail_to_sheets_intake, "settings_from_env", lambda: object())

    workflow = gmail_to_sheets_intake.get_workflow(cfg)
    alert_step = next(step for step in workflow.steps if step.name == "emit_alert_if_needs_review")

    def seed_state(_ctx: RunContext, state: RunState, _log: JsonlLogger) -> StepResult:
        state.data["needs_review_new_count"] = 99
        state.data["gmail_needs_review_label_name"] = "gw/needs-review"
        return StepResult(ok=True, outputs={"needs_review_new_count": 99})

    ctx = RunContext.create(tmp_path / "runs")
    log = JsonlLogger(path=ctx.logs_path, component="engine")
    result = run_workflow(
        workflow=Workflow(
            name="gmail_to_sheets_intake_alerts",
            steps=[Step(name="seed_state", fn=seed_state), alert_step],
        ),
        ctx=ctx,
        log=log,
    )

    assert result.ok is True
    assert called is False
    assert not (ctx.artifacts_dir / "needs_review_alert.json").exists()
    assert not ctx.artifacts_index_path.exists()

    logs = _as_jsonl_lines(ctx.logs_path)
    disabled = next(event for event in logs if event["event"] == "needs_review_alert_disabled")
    assert disabled["workflow"] == "gmail_to_sheets_intake"
    assert disabled["run_id"] == ctx.run_id
