from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from gw_engine.contracts import RunState, Step, StepResult, Workflow
from gw_engine.engine import run_workflow
from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


def test_sequential_success_persists_context(tmp_path: Path) -> None:
    executed: list[str] = []

    def step_one(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        executed.append("one")
        state.data["a"] = 1
        return StepResult(ok=True, outputs={"a": 1})

    def step_two(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        executed.append("two")
        state.data["b"] = 2
        return StepResult(ok=True, outputs={"b": 2})

    runs_dir = tmp_path / "runs"
    ctx = RunContext.create(runs_dir)
    log = JsonlLogger(path=ctx.logs_path, component="engine")
    workflow = Workflow(
        name="ok",
        steps=[
            Step(name="one", fn=step_one),
            Step(name="two", fn=step_two),
        ],
    )

    result = run_workflow(workflow=workflow, ctx=ctx, log=log)

    assert result.ok is True
    assert executed == ["one", "two"]

    context_path = ctx.run_dir / "context.json"
    assert context_path.exists()
    payload = _load_json(context_path)
    assert payload["data"] == {"a": 1, "b": 2}
    assert payload["step_outputs"]["one"] == {"a": 1}
    assert payload["step_outputs"]["two"] == {"b": 2}


def test_stop_on_explicit_failure_persists_context(tmp_path: Path) -> None:
    executed: list[str] = []

    def step_one(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        executed.append("one")
        state.data["a"] = 1
        return StepResult(ok=True, outputs={"a": 1})

    def step_fail(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        executed.append("fail")
        return StepResult(ok=False, outputs={"fail": True}, error="nope")

    def step_three(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        executed.append("three")
        return StepResult(ok=True)

    runs_dir = tmp_path / "runs"
    ctx = RunContext.create(runs_dir)
    log = JsonlLogger(path=ctx.logs_path, component="engine")
    workflow = Workflow(
        name="fail",
        steps=[
            Step(name="one", fn=step_one),
            Step(name="fail", fn=step_fail),
            Step(name="three", fn=step_three),
        ],
    )

    result = run_workflow(workflow=workflow, ctx=ctx, log=log)

    assert result.ok is False
    assert result.failed_step == "fail"
    assert executed == ["one", "fail"]

    context_path = ctx.run_dir / "context.json"
    assert context_path.exists()
    payload = _load_json(context_path)
    assert payload["data"] == {"a": 1}
    assert payload["step_outputs"]["one"] == {"a": 1}
    assert payload["step_outputs"]["fail"] == {"fail": True}


def test_stop_on_exception_persists_context_and_logs_error(tmp_path: Path) -> None:
    executed: list[str] = []

    def step_one(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        executed.append("one")
        state.data["a"] = 1
        return StepResult(ok=True)

    def step_boom(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        executed.append("boom")
        raise RuntimeError("boom")

    def step_three(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        executed.append("three")
        return StepResult(ok=True)

    runs_dir = tmp_path / "runs"
    ctx = RunContext.create(runs_dir)
    log = JsonlLogger(path=ctx.logs_path, component="engine")
    workflow = Workflow(
        name="boom",
        steps=[
            Step(name="one", fn=step_one),
            Step(name="boom", fn=step_boom),
            Step(name="three", fn=step_three),
        ],
    )

    result = run_workflow(workflow=workflow, ctx=ctx, log=log)

    assert result.ok is False
    assert result.failed_step == "boom"
    assert executed == ["one", "boom"]

    context_path = ctx.run_dir / "context.json"
    assert context_path.exists()
    payload = _load_json(context_path)
    assert payload["data"] == {"a": 1}

    with ctx.logs_path.open("r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f]

    assert any(
        r.get("event") == "step_error" and r.get("error_type") == "RuntimeError" for r in records
    )
