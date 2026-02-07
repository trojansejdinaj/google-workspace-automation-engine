from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, cast

import pytest

from gw_engine.cli import main
from gw_engine.engine import demo_steps, run_steps
from gw_engine.exporters import export_run_audit


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return cast(list[dict[str, Any]], json.load(f))


def test_run_persists_run_and_step_summaries(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    ctx = run_steps(runs_dir=runs_dir, steps=demo_steps())

    run_payload = _load_json(ctx.run_dir / "run.json")
    steps_payload = _load_json_list(ctx.run_dir / "steps.json")

    assert run_payload["run_id"] == ctx.run_id
    assert run_payload["workflow"] == "adhoc"
    assert run_payload["status"] == "OK"
    assert isinstance(run_payload["duration_ms"], int)
    assert isinstance(run_payload["started_at"], str)
    assert isinstance(run_payload["finished_at"], str)
    assert run_payload["error_summary"] is None

    assert len(steps_payload) == 2
    assert [x["step_name"] for x in steps_payload] == ["demo_one", "demo_two"]
    assert all(x["status"] == "OK" for x in steps_payload)
    assert all(isinstance(x["duration_ms"], int) for x in steps_payload)


def test_export_json_creates_bundle(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    ctx = run_steps(runs_dir=runs_dir, steps=demo_steps())

    out = export_run_audit(runs_dir=runs_dir, run_id=ctx.run_id, fmt="json")

    payload = _load_json(out)
    assert out == ctx.run_dir / "audit.json"
    assert set(payload.keys()) == {"run", "steps"}
    assert payload["run"]["run_id"] == ctx.run_id
    assert len(payload["steps"]) == 2


def test_export_csv_creates_rows_per_step(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    ctx = run_steps(runs_dir=runs_dir, steps=demo_steps())

    out = export_run_audit(runs_dir=runs_dir, run_id=ctx.run_id, fmt="csv")

    with out.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    assert out == ctx.run_dir / "audit.csv"
    assert len(rows) == 2
    assert all(row["run_id"] == ctx.run_id for row in rows)
    assert [row["step_name"] for row in rows] == ["demo_one", "demo_two"]


def test_export_invalid_run_id_errors_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs_dir = tmp_path / "runs"
    monkeypatch.setenv("GW_RUNS_DIR", str(runs_dir))
    monkeypatch.setattr(sys, "argv", ["gw", "export", "missing-run-id", "--format", "json"])

    with pytest.raises(SystemExit) as e:
        main()

    assert "run_id not found" in str(e.value)


def test_rerun_creates_new_run_id_and_preserves_history(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"

    ctx_one = run_steps(runs_dir=runs_dir, steps=demo_steps())
    ctx_two = run_steps(runs_dir=runs_dir, steps=demo_steps())

    assert ctx_one.run_id != ctx_two.run_id
    assert (runs_dir / ctx_one.run_id / "run.json").exists()
    assert (runs_dir / ctx_two.run_id / "run.json").exists()
