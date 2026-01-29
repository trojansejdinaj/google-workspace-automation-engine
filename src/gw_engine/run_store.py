from __future__ import annotations

from pathlib import Path

from gw_engine.run_context import RunContext


def create_run(runs_dir: Path) -> RunContext:
    return RunContext.create(runs_dir)
