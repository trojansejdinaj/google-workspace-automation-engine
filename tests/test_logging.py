from __future__ import annotations

import json
from pathlib import Path

from gw_engine.engine import demo_steps, run_steps


def test_demo_writes_jsonl_logs(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    ctx = run_steps(runs_dir=runs_dir, steps=demo_steps())

    assert ctx.logs_path.exists()
    lines = ctx.logs_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 4  # run_start + step_start/end + run_end (plus demo events)

    first = json.loads(lines[0])
    assert {"ts", "level", "component", "event"} <= set(first.keys())
    assert first["component"] == "engine"

    # ensure run_id is present in run events
    run_start = json.loads(lines[0])
    assert run_start["event"] == "run_start"
    assert run_start["run_id"] == ctx.run_id

    # ensure we have step_start and step_end with duration_ms
    events = [json.loads(x)["event"] for x in lines]
    assert "step_start" in events
    assert "step_end" in events
