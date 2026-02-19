"""Tests for engine failure handling with APIRetryExhausted and error artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from gw_engine.contracts import RunState, Step, StepResult, StepStatus, Workflow
from gw_engine.engine import run_workflow
from gw_engine.exceptions import APIRetryExhausted
from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext


def test_api_retry_exhausted_marks_step_failed_and_creates_error_artifact(tmp_path: Path) -> None:
    """Test that APIRetryExhausted creates error artifact and marks step as FAILED."""
    executed: list[str] = []

    def failing_step(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        executed.append("failing_step")
        raise APIRetryExhausted(
            operation="sheets.spreadsheets.values.get",
            attempts=5,
            status_code=429,
            reason="rateLimitExceeded",
            message="Rate limit exceeded after 5 attempts",
        )

    def should_not_run(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        executed.append("should_not_run")
        return StepResult(ok=True)

    # Create workflow with failing first step
    runs_dir = tmp_path / "runs"
    ctx = RunContext.create(runs_dir)
    log = JsonlLogger(path=ctx.logs_path, component="engine")
    workflow = Workflow(
        name="test_workflow",
        steps=[
            Step(name="failing_step", fn=failing_step),
            Step(name="should_not_run", fn=should_not_run),
        ],
    )

    result = run_workflow(workflow=workflow, ctx=ctx, log=log)

    # Verify workflow result
    assert result.ok is False
    assert result.failed_step == "failing_step"
    assert "Rate limit exceeded" in result.error

    # Verify execution stopped at first failure
    assert executed == ["failing_step"]

    # Verify error artifact was created
    error_artifact_path = ctx.run_dir / "errors" / "test_workflow__failing_step.json"
    assert error_artifact_path.exists(), f"Error artifact should exist at {error_artifact_path}"

    # Verify error artifact content
    with error_artifact_path.open("r") as f:
        error_content = json.load(f)

    assert error_content["run_id"] == ctx.run_id
    assert error_content["workflow"] == "test_workflow"
    assert error_content["step"] == "failing_step"
    assert error_content["status"] == "FAILED"
    assert error_content["error_type"] == "APIRetryExhausted"
    assert error_content["error_message"] == str(
        APIRetryExhausted(
            operation="sheets.spreadsheets.values.get",
            attempts=5,
            status_code=429,
            reason="rateLimitExceeded",
            message="Rate limit exceeded after 5 attempts",
        )
    )
    assert error_content["operation"] == "sheets.spreadsheets.values.get"
    assert error_content["status_code"] == 429
    assert error_content["attempts"] == 5
    assert error_content["reason"] == "rateLimitExceeded"
    assert "ts" in error_content

    # Verify step_failed log event
    with ctx.logs_path.open("r") as f:
        log_lines = [json.loads(line) for line in f if line.strip()]

    step_failed_events = [e for e in log_lines if e.get("event") == "step_failed"]
    assert len(step_failed_events) == 1

    failed_event = step_failed_events[0]
    assert failed_event["workflow"] == "test_workflow"
    assert failed_event["step"] == "failing_step"
    assert failed_event["step_idx"] == 1
    assert failed_event["error_type"] == "APIRetryExhausted"
    assert failed_event["operation"] == "sheets.spreadsheets.values.get"
    assert failed_event["status_code"] == 429
    assert failed_event["attempts"] == 5
    assert failed_event["reason"] == "rateLimitExceeded"
    assert failed_event["error_artifact_path"] == "errors/test_workflow__failing_step.json"

    # Verify run finalization occurred
    run_summary_path = ctx.run_dir / "run.json"
    assert run_summary_path.exists(), "Run summary should be written"

    with run_summary_path.open("r") as f:
        run_summary = json.load(f)

    assert run_summary["run_id"] == ctx.run_id
    assert run_summary["workflow"] == "test_workflow"
    assert run_summary["status"] == StepStatus.FAILED.value
    assert run_summary["error_summary"] is not None

    # Verify steps summary
    steps_summary_path = ctx.run_dir / "steps.json"
    assert steps_summary_path.exists(), "Steps summary should be written"

    with steps_summary_path.open("r") as f:
        steps_summary = json.load(f)

    assert len(steps_summary) == 1  # Only first step executed
    assert steps_summary[0]["step_name"] == "failing_step"
    assert steps_summary[0]["status"] == StepStatus.FAILED.value
    assert steps_summary[0]["error_summary"] is not None

    # Verify run_end event was logged
    run_end_events = [e for e in log_lines if e.get("event") == "run_end"]
    assert len(run_end_events) == 1
    assert run_end_events[0]["ok"] is False


def test_generic_exception_marks_step_failed_with_error_artifact(tmp_path: Path) -> None:
    """Test that non-APIRetryExhausted exceptions also create error artifacts."""

    def failing_step(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        raise ValueError("Invalid configuration detected")

    runs_dir = tmp_path / "runs"
    ctx = RunContext.create(runs_dir)
    log = JsonlLogger(path=ctx.logs_path, component="engine")
    workflow = Workflow(
        name="validation_workflow",
        steps=[Step(name="validate_config", fn=failing_step)],
    )

    result = run_workflow(workflow=workflow, ctx=ctx, log=log)

    # Verify workflow result
    assert result.ok is False
    assert result.failed_step == "validate_config"

    # Verify error artifact was created
    error_artifact_path = ctx.run_dir / "errors" / "validation_workflow__validate_config.json"
    assert error_artifact_path.exists()

    with error_artifact_path.open("r") as f:
        error_content = json.load(f)

    assert error_content["error_type"] == "ValueError"
    assert error_content["error_message"] == "Invalid configuration detected"
    assert error_content["status"] == "FAILED"
    # Should NOT have API-specific fields for non-API exceptions
    assert "operation" not in error_content
    assert "status_code" not in error_content
    assert "attempts" not in error_content

    # Verify step_failed log event
    with ctx.logs_path.open("r") as f:
        log_lines = [json.loads(line) for line in f if line.strip()]

    step_failed_events = [e for e in log_lines if e.get("event") == "step_failed"]
    assert len(step_failed_events) == 1

    failed_event = step_failed_events[0]
    assert failed_event["error_type"] == "ValueError"
    assert "operation" not in failed_event  # No API metadata

    # Verify run finalized
    assert (ctx.run_dir / "run.json").exists()
    assert (ctx.run_dir / "steps.json").exists()


def test_step_result_failure_creates_error_artifact(tmp_path: Path) -> None:
    """Test that StepResult(ok=False) also creates error artifacts."""

    def failing_step(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        return StepResult(ok=False, error="Business logic validation failed")

    runs_dir = tmp_path / "runs"
    ctx = RunContext.create(runs_dir)
    log = JsonlLogger(path=ctx.logs_path, component="engine")
    workflow = Workflow(
        name="business_workflow",
        steps=[Step(name="validate_business_rules", fn=failing_step)],
    )

    result = run_workflow(workflow=workflow, ctx=ctx, log=log)

    # Verify workflow result
    assert result.ok is False
    assert result.failed_step == "validate_business_rules"
    assert result.error == "Business logic validation failed"

    # Verify error artifact was created
    error_artifact_path = ctx.run_dir / "errors" / "business_workflow__validate_business_rules.json"
    assert error_artifact_path.exists()

    with error_artifact_path.open("r") as f:
        error_content = json.load(f)

    assert error_content["error_type"] == "StepFailed"
    assert error_content["error_message"] == "Business logic validation failed"
    assert error_content["status"] == "FAILED"

    # Verify run finalized properly
    run_summary_path = ctx.run_dir / "run.json"
    assert run_summary_path.exists()

    with run_summary_path.open("r") as f:
        run_summary = json.load(f)

    assert run_summary["status"] == StepStatus.FAILED.value


def test_partial_failure_preserves_successful_step_outputs(tmp_path: Path) -> None:
    """Test that partial failure preserves outputs from successful steps."""
    executed: list[str] = []

    def successful_step(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        executed.append("successful_step")
        state.data["result"] = "success"
        return StepResult(ok=True, outputs={"rows_processed": 100})

    def failing_step(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        executed.append("failing_step")
        # Can access state from previous step
        assert state.data["result"] == "success"
        raise APIRetryExhausted(
            operation="sheets.spreadsheets.values.append",
            attempts=3,
            status_code=503,
            message="Service unavailable",
        )

    runs_dir = tmp_path / "runs"
    ctx = RunContext.create(runs_dir)
    log = JsonlLogger(path=ctx.logs_path, component="engine")
    workflow = Workflow(
        name="partial_workflow",
        steps=[
            Step(name="successful_step", fn=successful_step),
            Step(name="failing_step", fn=failing_step),
        ],
    )

    result = run_workflow(workflow=workflow, ctx=ctx, log=log)

    assert result.ok is False
    assert result.failed_step == "failing_step"
    assert executed == ["successful_step", "failing_step"]

    # Verify context preserved successful step data
    context_path = ctx.run_dir / "context.json"
    assert context_path.exists()

    with context_path.open("r") as f:
        context = json.load(f)

    assert context["data"]["result"] == "success"
    assert context["step_outputs"]["successful_step"] == {"rows_processed": 100}

    # Verify steps summary includes both steps
    steps_summary_path = ctx.run_dir / "steps.json"
    with steps_summary_path.open("r") as f:
        steps_summary = json.load(f)

    assert len(steps_summary) == 2
    assert steps_summary[0]["step_name"] == "successful_step"
    assert steps_summary[0]["status"] == StepStatus.OK.value
    assert steps_summary[0]["metrics"] == {"rows_processed": 100}

    assert steps_summary[1]["step_name"] == "failing_step"
    assert steps_summary[1]["status"] == StepStatus.FAILED.value

    # Verify error artifact for failing step
    error_artifact_path = ctx.run_dir / "errors" / "partial_workflow__failing_step.json"
    assert error_artifact_path.exists()


def test_multiple_error_artifacts_for_different_runs(tmp_path: Path) -> None:
    """Test that different runs create separate error artifacts."""

    def failing_step(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        raise ValueError(f"Failure in run {ctx.run_id}")

    runs_dir = tmp_path / "runs"

    # Run 1
    ctx1 = RunContext.create(runs_dir)
    log1 = JsonlLogger(path=ctx1.logs_path, component="engine")
    workflow1 = Workflow(name="test", steps=[Step(name="step1", fn=failing_step)])
    run_workflow(workflow=workflow1, ctx=ctx1, log=log1)

    # Run 2
    ctx2 = RunContext.create(runs_dir)
    log2 = JsonlLogger(path=ctx2.logs_path, component="engine")
    workflow2 = Workflow(name="test", steps=[Step(name="step1", fn=failing_step)])
    run_workflow(workflow=workflow2, ctx=ctx2, log=log2)

    # Verify both error artifacts exist in separate run directories
    error1 = ctx1.run_dir / "errors" / "test__step1.json"
    error2 = ctx2.run_dir / "errors" / "test__step1.json"

    assert error1.exists()
    assert error2.exists()
    assert error1 != error2  # Different paths

    with error1.open("r") as f:
        content1 = json.load(f)

    with error2.open("r") as f:
        content2 = json.load(f)

    assert content1["run_id"] == ctx1.run_id
    assert content2["run_id"] == ctx2.run_id
    assert content1["run_id"] != content2["run_id"]
