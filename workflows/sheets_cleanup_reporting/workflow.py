# ruff: noqa: UP017
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from typing import Any

from gw_engine.clients import build_service, settings_from_env
from gw_engine.config import load_config
from gw_engine.contracts import RunState, Step, StepResult, Workflow
from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext
from gw_engine.sheets_transforms import apply_transforms, dedupe_rows
from gw_engine.sheets_validation import build_schema_from_cfg, mark_rows_with_reasons, validate_rows


def _write_tab_values(*, sheets_svc: Any, sheet_id: str, tab: str, values: list[list[Any]]) -> None:
    """Write values to a sheet tab starting at A1.

    IDEMPOTENCY: This writes from A1 onwards. Always call _clear_tab() first
    to ensure old data doesn't persist if the new data set is smaller.
    """
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
    """Clear all data from a sheet tab.

    IDEMPOTENCY: Clears entire tab to ensure clean slate for reruns.
    """
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
        if not sheet_id or sheet_id == "REPLACE_ME":
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
            {
                "id": "A-1",
                "date": "02/01/2026",
                "description": "  coffee  ",
                "amount": "1,200.00",
                "category": "Food",
            },  # duplicate id + messy inputs
        ]

        transforms_cfg = cfg.get("transforms", {})
        dedupe_cfg = cfg.get("dedupe", {})

        rows_in = len(rows)

        # Apply cleanup transforms (T3)
        schema_map = rules.get("schema", {})
        transformed, transform_invalid = apply_transforms(
            rows,
            schema=schema_map,
            transforms_cfg=transforms_cfg,
        )

        # Validate after transforms (T2 rules)
        result = validate_rows(transformed, schema)
        marked = mark_rows_with_reasons(transformed, result.invalid_rows)

        # Combine invalids (transform + validation)
        invalid_count = len(transform_invalid) + result.rows_invalid
        invalid_rate = (invalid_count / rows_in) if rows_in else 0.0

        # Dedupe valid rows (T3)
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
                [
                    str(x.row_idx + 1),
                    "; ".join(x.reasons),
                    json.dumps(x.row, ensure_ascii=False),
                ]
            )

        for x in result.invalid_rows:
            needs_review_values.append(
                [
                    str(x.row_idx + 1),
                    "; ".join(x.reasons),
                    json.dumps(x.row, ensure_ascii=False),
                ]
            )

        # IDEMPOTENCY: Write to Sheets using clear-then-write pattern.
        # This ensures reruns completely replace tab contents, avoiding duplicate rows.
        sheet_id = cfg["sheets"]["sheet_id"]
        tabs = cfg["tabs"]
        report_tab = tabs["report_tab"]
        needs_tab = tabs["needs_review_tab"]

        app_cfg = load_config()
        settings = settings_from_env()
        sheets_svc = build_service(cfg=app_cfg, api="sheets", settings=settings)

        _ensure_sheet_tabs(
            sheets_svc=sheets_svc,
            sheet_id=sheet_id,
            tab_names=[report_tab, needs_tab],
        )

        # Clear tabs completely before writing to ensure idempotent behavior
        _clear_tab(sheets_svc=sheets_svc, sheet_id=sheet_id, tab=report_tab)
        _clear_tab(sheets_svc=sheets_svc, sheet_id=sheet_id, tab=needs_tab)

        _write_tab_values(
            sheets_svc=sheets_svc,
            sheet_id=sheet_id,
            tab=report_tab,
            values=report_values,
        )
        _write_tab_values(
            sheets_svc=sheets_svc,
            sheet_id=sheet_id,
            tab=needs_tab,
            values=needs_review_values,
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

        # IDEMPOTENCY: Local artifacts use fixed names within run-specific directory.
        # Each run has unique ctx.run_dir, so reruns create new directories.
        # Within same run_id (manual rerun), files overwrite deterministically.
        artifacts_dir = ctx.run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        report_csv = artifacts_dir / "report.csv"
        needs_csv = artifacts_dir / "needs_review.csv"

        with report_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerows(report_values)

        with needs_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerows(needs_review_values)

        out = artifacts_dir / "cleanup_report.json"
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
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        log.info(
            "cleanup_done",
            rows_in=rows_in,
            invalid_count=invalid_count,
            dedupe_removed=dedupe_removed,
            rows_out=rows_out,
            artifact=str(out),
            report_csv=str(report_csv),
            needs_review_csv=str(needs_csv),
        )

        return StepResult(
            ok=True,
            outputs={
                "rows_in": rows_in,
                "invalid_count": invalid_count,
                "dedupe_removed": dedupe_removed,
                "rows_out": rows_out,
                "artifact": str(out),
            },
        )

    steps = [
        Step(name="validate_config", fn=validate_config),
        Step(name="validate_sample_rows", fn=validate_sample_rows),
    ]
    return Workflow(name=name, steps=steps)
