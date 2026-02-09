from __future__ import annotations

import json
from typing import Any

from gw_engine.contracts import RunState, Step, StepResult, Workflow
from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext


def get_workflow(cfg: dict[str, Any]) -> Workflow:
    name = "sheets_cleanup_reporting"

    def validate_config(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        # Minimal “contract validation” for scaffold
        sheet_id = cfg.get("sheets", {}).get("sheet_id")
        tabs = cfg.get("tabs", {})
        required = cfg.get("rules", {}).get("required_columns", [])

        missing = []
        if not sheet_id or sheet_id == "REPLACE_ME":
            missing.append("sheets.sheet_id")
        for k in ["input_tab", "cleaned_tab", "report_tab"]:
            if not tabs.get(k):
                missing.append(f"tabs.{k}")
        if not isinstance(required, list) or not required:
            missing.append("rules.required_columns")

        if missing:
            log.error("config_invalid", missing=missing)
            return StepResult(ok=False, error=f"Invalid config, missing: {missing}")

        log.info("config_valid", workflow=name, required_columns=len(required))
        state.data["cfg"] = cfg
        return StepResult(ok=True, outputs={"missing": 0})

    def write_stub_report(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        # Fake counts for scaffold proof (replace later with real Sheets I/O)
        report = {
            "workflow": name,
            "run_id": ctx.run_id,
            "counts": {
                "rows_in": 0,
                "rows_cleaned": 0,
                "rows_dropped": 0,
                "duplicates": 0,
                "invalid": 0,
            },
            "issues": [],
        }

        artifacts_dir = ctx.run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        out = artifacts_dir / "report.json"
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        log.info("report_written", path=str(out))
        return StepResult(ok=True, outputs={"artifact": str(out)})

    steps = [
        Step(name="validate_config", fn=validate_config),
        Step(name="write_stub_report", fn=write_stub_report),
    ]
    return Workflow(name=name, steps=steps)
