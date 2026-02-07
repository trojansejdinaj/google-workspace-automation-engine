from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, cast

RUN_SUMMARY_FILENAME = "run.json"
STEPS_SUMMARY_FILENAME = "steps.json"
AUDIT_JSON_FILENAME = "audit.json"
AUDIT_CSV_FILENAME = "audit.csv"

CSV_HEADERS = [
    "run_id",
    "workflow",
    "run_status",
    "run_started_at",
    "run_finished_at",
    "run_duration_ms",
    "step_name",
    "step_status",
    "step_started_at",
    "step_finished_at",
    "step_duration_ms",
    "step_error_summary",
    "step_metrics",
]


class ExportError(RuntimeError):
    pass


def _load_json_dict(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return cast(list[dict[str, Any]], json.load(f))


def resolve_run_dir(*, runs_dir: Path, run_id: str) -> Path:
    run_dir = runs_dir / run_id
    if not run_dir.exists() or not run_dir.is_dir():
        raise ExportError(f"run_id not found: {run_id} (expected directory: {run_dir})")
    return run_dir


def load_run_summaries(*, run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    run_summary_path = run_dir / RUN_SUMMARY_FILENAME
    steps_summary_path = run_dir / STEPS_SUMMARY_FILENAME
    if not run_summary_path.exists():
        raise ExportError(f"missing required summary file: {run_summary_path}")
    if not steps_summary_path.exists():
        raise ExportError(f"missing required summary file: {steps_summary_path}")

    run_summary = _load_json_dict(run_summary_path)
    steps_summary = _load_json_list(steps_summary_path)
    return run_summary, steps_summary


def _default_export_path(*, run_dir: Path, fmt: str) -> Path:
    if fmt == "json":
        return run_dir / AUDIT_JSON_FILENAME
    if fmt == "csv":
        return run_dir / AUDIT_CSV_FILENAME
    raise ExportError(f"unsupported format: {fmt}")


def export_run_audit(
    *, runs_dir: Path, run_id: str, fmt: str, out_path: Path | None = None
) -> Path:
    run_dir = resolve_run_dir(runs_dir=runs_dir, run_id=run_id)
    run_summary, steps_summary = load_run_summaries(run_dir=run_dir)

    output_path = out_path or _default_export_path(run_dir=run_dir, fmt=fmt)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "json":
        bundle = {"run": run_summary, "steps": steps_summary}
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(bundle, f, indent=2, sort_keys=True)
            f.write("\n")
        return output_path

    if fmt == "csv":
        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            for step in steps_summary:
                writer.writerow(
                    {
                        "run_id": run_summary.get("run_id", run_id),
                        "workflow": run_summary.get("workflow"),
                        "run_status": run_summary.get("status"),
                        "run_started_at": run_summary.get("started_at"),
                        "run_finished_at": run_summary.get("finished_at"),
                        "run_duration_ms": run_summary.get("duration_ms"),
                        "step_name": step.get("step_name"),
                        "step_status": step.get("status"),
                        "step_started_at": step.get("started_at"),
                        "step_finished_at": step.get("finished_at"),
                        "step_duration_ms": step.get("duration_ms"),
                        "step_error_summary": step.get("error_summary"),
                        "step_metrics": (
                            json.dumps(step["metrics"], sort_keys=True)
                            if step.get("metrics") is not None
                            else ""
                        ),
                    }
                )
        return output_path

    raise ExportError(f"unsupported format: {fmt}")
