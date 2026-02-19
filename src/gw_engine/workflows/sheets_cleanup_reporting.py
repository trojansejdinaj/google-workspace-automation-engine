# ruff: noqa: UP017
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from typing import Any

from gw_engine.artifacts import register_artifact
from gw_engine.clients import build_service, settings_from_env
from gw_engine.config import load_config
from gw_engine.contracts import RunState, Step, StepResult, Workflow
from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext
from gw_engine.sheets_transforms import apply_transforms, dedupe_rows
from gw_engine.sheets_validation import build_schema_from_cfg, mark_rows_with_reasons, validate_rows
from gw_engine.workflows import register as _register


def _write_tab_values(*, sheets_svc: Any, sheet_id: str, tab: str, values: list[list[Any]]) -> None:
    rng = f"{tab}!A1"
    sheets_svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=rng,
        valueInputOption="RAW",
        body={"values": values},
    ).execute()


def _ensure_sheet_tabs(*, sheets_svc: Any, sheet_id: str, tab_names: list[str]) -> None:
    ss = sheets_svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
    existing = {s["properties"]["title"] for s in ss.get("sheets", [])}

    requests = []
    for name in tab_names:
        if name not in existing:
            requests.append({"addSheet": {"properties": {"title": name}}})

    if requests:
        sheets_svc.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": requests},
        ).execute()


def _clear_tab(*, sheets_svc: Any, sheet_id: str, tab: str) -> None:
    sheets_svc.spreadsheets().values().clear(
        spreadsheetId=sheet_id,
        range=tab,
        body={},
    ).execute()


def get_workflow(cfg: dict[str, Any]) -> Workflow:
    name = "sheets_cleanup_reporting"

    def validate_config(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        sheet_id = cfg.get("sheets", {}).get("sheet_id")
        tabs = cfg.get("tabs", {})
        rules = cfg.get("rules", {})

        missing = []
        if not sheet_id or sheet_id == "REPLACE_ME" or sheet_id == "DUMMY_SHEET_ID":
            missing.append("sheets.sheet_id")
        for k in ["input_tab", "cleaned_tab", "report_tab", "needs_review_tab"]:
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

    def run_cleanup(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        rules = cfg.get("rules", {})
        schema = build_schema_from_cfg(rules)

        # NOTE: still sample-driven for now (Sheets read step can come later if you want)
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
            {
                "id": "A-1",
                "date": "02/01/2026",
                "description": "  coffee  ",
                "amount": "1,200.00",
                "category": "Food",
            },
        ]

        transforms_cfg = cfg.get("transforms", {})
        dedupe_cfg = cfg.get("dedupe", {})

        rows_in = len(rows)

        # 1) transforms
        schema_map = rules.get("schema", {})
        transformed, transform_invalid = apply_transforms(
            rows,
            schema=schema_map,
            transforms_cfg=transforms_cfg,
        )

        # 2) validation
        result = validate_rows(transformed, schema)
        marked = mark_rows_with_reasons(transformed, result.invalid_rows)

        invalid_count = len(transform_invalid) + result.rows_invalid
        invalid_rate = (invalid_count / rows_in) if rows_in else 0.0

        # 3) dedupe on valid rows
        dedupe_keys = list(dedupe_cfg.get("keys", []) or [])
        keep = dedupe_cfg.get("keep", "first")
        if dedupe_keys:
            deduped_valid, dedupe_removed = dedupe_rows(
                result.valid_rows, keys=dedupe_keys, keep=keep
            )
        else:
            deduped_valid, dedupe_removed = result.valid_rows, 0

        rows_out = len(deduped_valid)

        now_utc = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

        report_values: list[list[str]] = [
            ["metric", "value"],
            ["run_id", ctx.run_id],
            ["generated_at_utc", now_utc],
            ["rows_in", str(rows_in)],
            ["rows_valid_pre_dedupe", str(result.rows_valid)],
            ["invalid_count", str(invalid_count)],
            ["dedupe_removed", str(dedupe_removed)],
            ["rows_out", str(rows_out)],
            ["invalid_rate", f"{invalid_rate:.4f}"],
        ]

        needs_review_values: list[list[str]] = [["row_number", "reason", "values_json"]]
        for x in transform_invalid:
            needs_review_values.append(
                [str(x.row_idx + 1), "; ".join(x.reasons), json.dumps(x.row, ensure_ascii=False)]
            )
        for x in result.invalid_rows:
            needs_review_values.append(
                [str(x.row_idx + 1), "; ".join(x.reasons), json.dumps(x.row, ensure_ascii=False)]
            )

        # write to Sheets
        sheet_id = cfg["sheets"]["sheet_id"]
        tabs = cfg["tabs"]
        report_tab = tabs["report_tab"]
        needs_tab = tabs["needs_review_tab"]

        app_cfg = load_config()
        settings = settings_from_env()
        sheets_svc = build_service(cfg=app_cfg, api="sheets", settings=settings)

        _ensure_sheet_tabs(
            sheets_svc=sheets_svc, sheet_id=sheet_id, tab_names=[report_tab, needs_tab]
        )
        _clear_tab(sheets_svc=sheets_svc, sheet_id=sheet_id, tab=report_tab)
        _clear_tab(sheets_svc=sheets_svc, sheet_id=sheet_id, tab=needs_tab)

        _write_tab_values(
            sheets_svc=sheets_svc, sheet_id=sheet_id, tab=report_tab, values=report_values
        )
        _write_tab_values(
            sheets_svc=sheets_svc, sheet_id=sheet_id, tab=needs_tab, values=needs_review_values
        )

        log.info(
            "report_written",
            report_tab=report_tab,
            needs_review_tab=needs_tab,
            rows_in=rows_in,
            rows_out=rows_out,
            invalid_count=invalid_count,
            report_rows=len(report_values),
            needs_review_rows=len(needs_review_values) - 1,
        )

        # local artifacts
        report_csv = ctx.artifacts_dir / "report.csv"
        needs_csv = ctx.artifacts_dir / "needs_review.csv"
        cleanup_json = ctx.artifacts_dir / "cleanup_report.json"

        with report_csv.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(report_values)

        with needs_csv.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(needs_review_values)

        payload = {
            "workflow": name,
            "run_id": ctx.run_id,
            "counts": {
                "rows_in": rows_in,
                "invalid_count": invalid_count,
                "rows_out": rows_out,
                "dedupe_removed": dedupe_removed,
                "rows_valid_pre_dedupe": result.rows_valid,
            },
            "transform_invalid_examples": [
                {"row_idx": x.row_idx, "reasons": x.reasons, "row": x.row}
                for x in transform_invalid[:25]
            ],
            "validation_invalid_examples": [
                {"row_idx": x.row_idx, "reasons": x.reasons, "row": x.row}
                for x in result.invalid_rows[:25]
            ],
            "cleaned_preview": deduped_valid[:10],
            "marked_preview": marked[:10],
        }
        cleanup_json.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        # T5: register artifacts in the run index
        register_artifact(
            ctx,
            name="report_csv",
            path=report_csv,
            type="csv",
            metadata={"rows": len(report_values)},
        )
        register_artifact(
            ctx,
            name="needs_review_csv",
            path=needs_csv,
            type="csv",
            metadata={"rows": len(needs_review_values) - 1},
        )
        register_artifact(
            ctx,
            name="cleanup_report_json",
            path=cleanup_json,
            type="json",
            metadata={
                "rows_in": rows_in,
                "rows_out": rows_out,
                "invalid_count": invalid_count,
                "dedupe_removed": dedupe_removed,
            },
        )

        log.info(
            "cleanup_done",
            rows_in=rows_in,
            invalid_count=invalid_count,
            dedupe_removed=dedupe_removed,
            rows_out=rows_out,
            artifacts_index=str(ctx.artifacts_index_path.relative_to(ctx.run_dir).as_posix()),
        )

        return StepResult(
            ok=True,
            outputs={
                "rows_in": rows_in,
                "invalid_count": invalid_count,
                "dedupe_removed": dedupe_removed,
                "rows_out": rows_out,
                "artifacts_index": ctx.artifacts_index_path.relative_to(ctx.run_dir).as_posix(),
            },
        )

    steps = [
        Step(name="validate_config", fn=validate_config),
        Step(name="run_cleanup", fn=run_cleanup),
    ]
    return Workflow(name=name, steps=steps)


# register into built-in registry
_register("sheets_cleanup_reporting", get_workflow)
