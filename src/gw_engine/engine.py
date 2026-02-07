from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gw_engine.contracts import RunState, Step, StepResult, StepStatus, Workflow
from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext, duration_ms, now_ms


@dataclass(frozen=True)
class WorkflowResult:
    ok: bool
    run_id: str
    failed_step: str | None = None
    error: str | None = None


def _coerce_result(result: StepResult) -> StepResult:
    if isinstance(result, StepResult):
        return result
    raise TypeError("step must return StepResult")


def run_workflow(
    *,
    workflow: Workflow,
    ctx: RunContext,
    log: JsonlLogger,
    state: RunState | None = None,
) -> WorkflowResult:
    run_state = state or RunState()
    context_path = ctx.run_dir / "context.json"

    run_start = now_ms()
    log.info("run_start", run_id=ctx.run_id, workflow=workflow.name)
    ok = True
    failed_step: str | None = None
    error: str | None = None

    for idx, step in enumerate(workflow.steps, start=1):
        step_start = now_ms()
        log.info(
            "step_start",
            run_id=ctx.run_id,
            step=step.name,
            step_idx=idx,
            start_ms=step_start,
            status=StepStatus.RUNNING,
        )

        result: StepResult
        error_logged = False
        try:
            result = _coerce_result(step.run(ctx, run_state, log))
        except Exception as e:  # noqa: BLE001 (we want to capture anything)
            err_msg = str(e) or type(e).__name__
            result = StepResult(ok=False, error=err_msg)
            log.error(
                "step_error",
                run_id=ctx.run_id,
                step=step.name,
                step_idx=idx,
                error_type=type(e).__name__,
                error_message=err_msg,
            )
            error_logged = True

        if result.outputs is not None:
            run_state.step_outputs[step.name] = result.outputs

        if not result.ok:
            ok = False
            failed_step = step.name
            error = result.error or "step returned ok=false"
            if not error_logged:
                log.error(
                    "step_error",
                    run_id=ctx.run_id,
                    step=step.name,
                    step_idx=idx,
                    error_type="StepFailed",
                    error_message=error,
                )

        step_end = now_ms()
        log.info(
            "step_end",
            run_id=ctx.run_id,
            step=step.name,
            step_idx=idx,
            ok=result.ok,
            status=StepStatus.OK if result.ok else StepStatus.FAILED,
            duration_ms=duration_ms(step_start, step_end),
            end_ms=step_end,
        )

        run_state.persist(context_path)

        if not result.ok:
            break

    run_end = now_ms()
    log.info(
        "run_end",
        run_id=ctx.run_id,
        ok=ok,
        duration_ms=duration_ms(run_start, run_end),
        end_ms=run_end,
    )
    return WorkflowResult(ok=ok, run_id=ctx.run_id, failed_step=failed_step, error=error)


def run_steps_result(*, runs_dir: Path, steps: list[Step]) -> tuple[RunContext, WorkflowResult]:
    ctx = RunContext.create(runs_dir)
    log = JsonlLogger(path=ctx.logs_path, component="engine")
    workflow = Workflow(name="adhoc", steps=steps)
    result = run_workflow(workflow=workflow, ctx=ctx, log=log, state=RunState())
    return ctx, result


def run_steps(*, runs_dir: Path, steps: list[Step]) -> RunContext:
    ctx, _ = run_steps_result(runs_dir=runs_dir, steps=steps)
    return ctx


def demo_steps() -> list[Step]:
    def step_one(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        log.info("demo_event", run_id=ctx.run_id, step="demo_one", message="hello")
        state.data["demo_one"] = "ok"
        return StepResult(ok=True, outputs={"message": "hello"})

    def step_two(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        log.info("demo_event", run_id=ctx.run_id, step="demo_two", message="world")
        state.data["demo_two"] = "ok"
        return StepResult(ok=True, outputs={"message": "world"})

    return [
        Step(name="demo_one", fn=step_one),
        Step(name="demo_two", fn=step_two),
    ]
