from __future__ import annotations

from pathlib import Path

from gw_engine.run_context import RunContext


def test_run_context_creates_standard_run_directories(tmp_path: Path) -> None:
    ctx = RunContext.create(tmp_path / "runs")

    assert ctx.run_dir.is_dir()
    assert ctx.artifacts_dir.is_dir()
    assert (ctx.run_dir / "errors").is_dir()
    assert ctx.logs_path == ctx.run_dir / "logs.jsonl"
