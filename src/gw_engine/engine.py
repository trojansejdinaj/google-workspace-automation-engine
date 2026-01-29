from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext, duration_ms, now_ms
from gw_engine.run_store import create_run


@dataclass(frozen=True)
class Step:
    name: str
    fn: Callable[[RunContext, JsonlLogger], Any]


def run_steps(*, runs_dir: Path, steps: list[Step]) -> RunContext:
    ctx = create_run(runs_dir)
    log = JsonlLogger(path=ctx.logs_path, component="engine")

    run_start = now_ms()
    log.info("run_start", run_id=ctx.run_id)

    for idx, step in enumerate(steps, start=1):
        step_start = now_ms()
        log.info(
            "step_start",
            run_id=ctx.run_id,
            step=step.name,
            step_idx=idx,
            start_ms=step_start,
        )

        try:
            step.fn(ctx, log)
            ok = True
            err = None
        except Exception as e:  # noqa: BLE001 (we want to capture anything)
            ok = False
            err = {"error_type": type(e).__name__, "error_message": str(e)}
            log.error(
                "step_error",
                run_id=ctx.run_id,
                step=step.name,
                step_idx=idx,
                **err,
            )

        step_end = now_ms()
        log.info(
            "step_end",
            run_id=ctx.run_id,
            step=step.name,
            step_idx=idx,
            ok=ok,
            duration_ms=duration_ms(step_start, step_end),
            end_ms=step_end,
        )

        if not ok:
            break

    run_end = now_ms()
    log.info(
        "run_end",
        run_id=ctx.run_id,
        duration_ms=duration_ms(run_start, run_end),
        end_ms=run_end,
    )
    return ctx


def demo_steps() -> list[Step]:
    def step_one(ctx: RunContext, log: JsonlLogger) -> None:
        # placeholder work
        log.info("demo_event", run_id=ctx.run_id, step="demo_one", message="hello")

    def step_two(ctx: RunContext, log: JsonlLogger) -> None:
        log.info("demo_event", run_id=ctx.run_id, step="demo_two", message="world")

    return [
        Step(name="demo_one", fn=step_one),
        Step(name="demo_two", fn=step_two),
    ]
