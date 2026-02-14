from __future__ import annotations

import json
from typing import Any

from gw_engine.contracts import RunState, Step, StepResult, Workflow
from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext
from gw_engine.sheets_validation import build_schema_from_cfg, mark_rows_with_reasons, validate_rows


def get_workflow(cfg: dict[str, Any]) -> Workflow:
    name = "sheets_cleanup_reporting"

    def validate_config(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        sheet_id = cfg.get("sheets", {}).get("sheet_id")
        tabs = cfg.get("tabs", {})
        rules = cfg.get("rules", {})

        missing = []
        if not sheet_id or sheet_id == "REPLACE_ME":
            missing.append("sheets.sheet_id")
        for k in ["input_tab", "cleaned_tab", "report_tab"]:
            if not tabs.get(k):
                missing.append(f"tabs.{k}")

        try:
            schema = build_schema_from_cfg(rules)
        except Exception as e:
            log.error("schema_invalid", error=str(e))
            return StepResult(ok=False, error=f"Invalid schema: {e}")

        if not schema:
            missing.append("rules.schema (empty)")

        if missing:
            log.error("config_invalid", missing=missing)
            return StepResult(ok=False, error=f"Invalid config, missing: {missing}")

        log.info("config_valid", workflow=name, schema_cols=len(schema))
        state.data["cfg"] = cfg
        state.data["schema_cols"] = [c.__dict__ for c in schema]
        return StepResult(ok=True, outputs={"schema_cols": len(schema)})

    def validate_sample_rows(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        rules = cfg.get("rules", {})
        schema = build_schema_from_cfg(rules)

        # T2: in-memory sample; T3 will replace this with Sheets read
        rows = [
            {
                "id": "A-1",
                "date": "2026-02-01",
                "description": "Coffee",
                "amount": "3.50",
                "category": "Food",
            },
            {
                "id": "",
                "date": "2026-02-02",
                "description": "Taxi",
                "amount": "12.00",
            },  # invalid: id blank
            {
                "id": "A-3",
                "date": "02/03/2026",
                "description": "Lunch",
                "amount": "9.20",
            },  # invalid: date format
            {
                "id": "A-4",
                "date": "2026-02-04",
                "description": "Book",
                "amount": "abc",
            },  # invalid: amount
        ]

        result = validate_rows(rows, schema)
        marked = mark_rows_with_reasons(rows, result.invalid_rows)

        artifacts_dir = ctx.run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        out = artifacts_dir / "validation_report.json"
        payload = {
            "workflow": name,
            "run_id": ctx.run_id,
            "counts": {
                "rows_in": result.rows_in,
                "rows_valid": result.rows_valid,
                "rows_invalid": result.rows_invalid,
            },
            "invalid_examples": [
                {"row_idx": x.row_idx, "reasons": x.reasons, "row": x.row}
                for x in result.invalid_rows[:25]
            ],
            "marked_preview": marked[:10],
        }
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        log.info(
            "validation_done",
            rows_in=result.rows_in,
            rows_valid=result.rows_valid,
            rows_invalid=result.rows_invalid,
            artifact=str(out),
        )

        return StepResult(
            ok=True,
            outputs={
                "rows_in": result.rows_in,
                "rows_valid": result.rows_valid,
                "rows_invalid": result.rows_invalid,
                "artifact": str(out),
            },
        )

    steps = [
        Step(name="validate_config", fn=validate_config),
        Step(name="validate_sample_rows", fn=validate_sample_rows),
    ]
    return Workflow(name=name, steps=steps)
