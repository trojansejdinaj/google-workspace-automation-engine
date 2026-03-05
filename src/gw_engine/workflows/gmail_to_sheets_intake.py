from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from gw_engine.artifacts import register_artifact
from gw_engine.attachments import (
    ValidationStatus,
    quarantine_attachment,
    route_attachment,
    validate_attachment,
)
from gw_engine.clients import build_service, settings_from_env
from gw_engine.config import load_config
from gw_engine.contracts import RunState, Step, StepResult, Workflow
from gw_engine.gmail_actions import ActionItem, build_action_plan, summarize_plan
from gw_engine.gmail_adapter import GmailAdapter
from gw_engine.gmail_decode import decode_message_bodies
from gw_engine.logger import JsonlLogger
from gw_engine.parsing.contracts import ParsedEmail
from gw_engine.parsing.email_parser import parse_email
from gw_engine.run_context import RunContext
from gw_engine.sheets_triage import upsert_triage_table
from gw_engine.workflows import register as _register


def _as_int(value: Any, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return default
        try:
            return int(s)
        except ValueError:
            return default
    return default


def _as_float(value: Any, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return default
        try:
            return float(s)
        except ValueError:
            return default
    return default


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in {0, 1}:
            return bool(value)
        return default
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "y", "on"}:
            return True
        if v in {"false", "0", "no", "n", "off"}:
            return False
        return default
    return default


def _header_value(message: dict[str, Any], name: str) -> str:
    payload = message.get("payload")
    if not isinstance(payload, dict):
        return ""

    headers = payload.get("headers")
    if not isinstance(headers, list):
        return ""

    target = name.lower()
    for header in headers:
        if not isinstance(header, dict):
            continue
        h_name = str(header.get("name") or "").strip().lower()
        if h_name == target:
            return str(header.get("value") or "")
    return ""


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    tmp.replace(path)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            json.dump(row, f, sort_keys=True)
            f.write("\n")
    tmp.replace(path)


def _safe_name_component(value: str) -> str:
    safe = "".join(
        "_" if ch in {"\\", "/", ":", "*", "?", '"', "<", ">", "|"} else ch for ch in value
    )
    return safe.strip().strip(".")


def _safe_attachment_filename(filename: str, message_id: str, part_id: str | None) -> str:
    base = (filename or "").strip()
    fallback = f"{message_id}_{part_id}" if part_id else message_id
    cleaned = _safe_name_component(base or fallback)
    printable = "".join(ch for ch in cleaned if ch.isprintable())
    printable = printable.replace("\n", " ").replace("\r", " ").strip()
    if not printable:
        printable = f"{fallback}.bin"
    return printable[:180] if len(printable) > 180 else printable


def _next_available_file_path(directory: Path, filename: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    for idx in range(1, 1000):
        candidate = directory / f"{stem}-{idx}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Unable to allocate unique attachment filename for {filename}")


def _write_jsonl_append(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row))
            f.write("\n")


def get_workflow(cfg: dict[str, Any]) -> Workflow:
    name = "gmail_to_sheets_intake"

    def validate_config(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        gmail_cfg = cfg.get("gmail")
        if not isinstance(gmail_cfg, dict):
            return StepResult(ok=False, error="Invalid config: missing gmail section")

        query = str(gmail_cfg.get("gmail_query") or "").strip()
        if not query:
            return StepResult(ok=False, error="Invalid config: missing gmail.gmail_query")

        labels_cfg = gmail_cfg.get("labels")
        if not isinstance(labels_cfg, dict):
            return StepResult(ok=False, error="Invalid config: missing gmail.labels section")

        success_label = str(labels_cfg.get("success") or "").strip()
        needs_review_label = str(labels_cfg.get("needs_review") or "").strip()
        error_label = str(labels_cfg.get("error") or "").strip()
        if not success_label or not needs_review_label or not error_label:
            return StepResult(
                ok=False,
                error="Invalid config: gmail.labels must include non-empty success/needs_review/error",
            )

        options_cfg = cfg.get("options")
        options_map = options_cfg if isinstance(options_cfg, dict) else {}
        max_messages = max(1, _as_int(options_map.get("max_messages"), 50))
        min_confidence = _as_float(options_map.get("min_confidence"), 0.6)
        archive_on_success = _as_bool(options_map.get("archive_on_success"), False)
        archive_on_failure = _as_bool(options_map.get("archive_on_failure"), False)
        attachments_cfg = cfg.get("attachments")
        attachments_map = attachments_cfg if isinstance(attachments_cfg, dict) else {}
        attachments_enabled = _as_bool(attachments_map.get("enabled"), False)
        attachments_route_mode = (
            str(attachments_map.get("route_mode") or "artifacts").strip().lower()
        )
        if not attachments_route_mode:
            attachments_route_mode = "artifacts"
        attachments_drive_folder_id = str(attachments_map.get("drive_folder_id") or "").strip()

        if attachments_enabled and attachments_route_mode not in {"artifacts", "drive"}:
            return StepResult(
                ok=False,
                error="Invalid config: attachments.route_mode must be 'artifacts' or 'drive'",
            )
        if (
            attachments_enabled
            and attachments_route_mode == "drive"
            and not attachments_drive_folder_id
        ):
            return StepResult(
                ok=False,
                error="Invalid config: attachments.drive_folder_id required when route_mode is drive",
            )

        attachments_config = {
            "enabled": attachments_enabled,
            "max_size_bytes": attachments_map.get("max_size_bytes"),
            "allowed_mime_types": attachments_map.get("allowed_mime_types"),
            "allowed_extensions": attachments_map.get("allowed_extensions"),
            "route_mode": attachments_route_mode,
            "drive_folder_id": attachments_drive_folder_id,
        }

        state.data["gmail_query"] = query
        state.data["max_messages"] = max_messages
        state.data["gmail_success_label_name"] = success_label
        state.data["gmail_needs_review_label_name"] = needs_review_label
        state.data["gmail_error_label_name"] = error_label
        state.data["gmail_min_confidence"] = min_confidence
        state.data["gmail_archive_on_success"] = archive_on_success
        state.data["gmail_archive_on_failure"] = archive_on_failure
        state.data["attachments_enabled"] = attachments_enabled
        state.data["attachments_config"] = attachments_config

        log.info(
            "config_valid",
            workflow=name,
            query=query,
            max_messages=max_messages,
            gmail_success_label=success_label,
            gmail_needs_review_label=needs_review_label,
            gmail_error_label=error_label,
            min_confidence=min_confidence,
            archive_on_success=archive_on_success,
            archive_on_failure=archive_on_failure,
            attachments_enabled=attachments_enabled,
            attachments_route_mode=attachments_route_mode,
        )
        return StepResult(ok=True, outputs={"max_messages": max_messages})

    def collect_intake(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        query = str(state.data.get("gmail_query") or "").strip()
        max_messages = _as_int(state.data.get("max_messages"), 50)

        app_cfg = load_config()
        settings = settings_from_env()
        gmail_service = build_service(cfg=app_cfg, api="gmail", settings=settings)
        adapter = GmailAdapter(service=gmail_service, logger=log, run_id=ctx.run_id)

        message_ids = adapter.search_message_ids(query=query, max_results=max_messages)
        messages = adapter.fetch_messages(message_ids, format="full")
        state.data["message_ids"] = message_ids

        decoded_plain_count = 0
        decoded_html_count = 0
        decoded_none_count = 0
        action_items: list[ActionItem] = []

        intake_items: list[dict[str, Any]] = []
        for message in messages:
            decoded = decode_message_bodies(message)
            chosen = str(decoded.get("chosen") or "none")
            if chosen == "plain":
                decoded_plain_count += 1
            elif chosen == "html":
                decoded_html_count += 1
            else:
                decoded_none_count += 1

            message_id = str(message.get("id") or "")
            from_addr = _header_value(message, "From")
            to_addr = _header_value(message, "To")
            subject = _header_value(message, "Subject")
            date = _header_value(message, "Date")

            body_text = str(decoded.get("text") or "")
            parsed: ParsedEmail = parse_email(subject=subject, from_addr=from_addr, body=body_text)

            log.info(
                "email_parsed",
                message_id=message_id,
                confidence=parsed.confidence,
                parsed_keys=list(parsed.fields.keys()),
                error_count=len(parsed.errors),
            )

            warnings_any = decoded.get("warnings")
            warnings = (
                [str(w) for w in warnings_any]
                if isinstance(warnings_any, list)
                else [str(warnings_any)]
                if warnings_any is not None
                else []
            )

            parse_errors = [
                {
                    "code": error.code,
                    "message": error.message,
                    "field": error.field,
                }
                for error in parsed.errors
            ]
            error_count = len(parsed.errors)
            parse_ok = error_count == 0

            action_items.append(
                ActionItem(
                    message_id=message_id,
                    parse_ok=parse_ok,
                    error_count=error_count,
                    confidence=parsed.confidence,
                )
            )

            intake_items.append(
                {
                    "message_id": message_id,
                    "thread_id": str(message.get("threadId") or ""),
                    "internal_date": str(message.get("internalDate") or ""),
                    "from": from_addr,
                    "to": to_addr,
                    "subject": subject,
                    "date": date,
                    "body_text": body_text,
                    "body_chosen": chosen,
                    "decode_warnings": warnings,
                    "parsed": parsed.fields,
                    "parser_confidence": parsed.confidence,
                    "parser_errors": parse_errors,
                    "parse_confidence": parsed.confidence,
                    "parse_errors": parse_errors,
                }
            )

        state.data["action_items"] = action_items

        triage_rows = [
            {
                "message_id": str(item.get("message_id") or ""),
                "thread_id": str(item.get("thread_id") or ""),
                "from": str(item.get("from") or ""),
                "subject": str(item.get("subject") or ""),
                "date": str(item.get("date") or ""),
                "parsed": item.get("parsed") if isinstance(item.get("parsed"), dict) else {},
                "parser_confidence": item.get("parser_confidence", item.get("parse_confidence")),
            }
            for item in intake_items
        ]
        state.data["triage_rows"] = triage_rows

        if intake_items:
            first_preview = str(intake_items[0].get("body_text") or "")[:120]
            log.debug("gmail_decode_preview", run_id=ctx.run_id, body_preview_120=first_preview)

        ids_found = len(message_ids)
        fetched_count = len(messages)

        log.info(
            "gmail_intake_summary",
            run_id=ctx.run_id,
            ids_found=ids_found,
            fetched_count=fetched_count,
            decoded_plain_count=decoded_plain_count,
            decoded_html_count=decoded_html_count,
            decoded_none_count=decoded_none_count,
        )

        intake_path = ctx.artifacts_dir / "gmail_intake_items.json"
        summary_path = ctx.artifacts_dir / "gmail_intake_summary.json"
        parsed_emails_path = ctx.artifacts_dir / "parsed_emails.jsonl"

        summary_payload = {
            "run_id": ctx.run_id,
            "workflow": name,
            "query": query,
            "max_messages": max_messages,
            "ids_found": ids_found,
            "fetched_count": fetched_count,
            "decoded_plain_count": decoded_plain_count,
            "decoded_html_count": decoded_html_count,
            "decoded_none_count": decoded_none_count,
            "preview": [
                {
                    "message_id": item["message_id"],
                    "subject": item["subject"],
                    "body_preview_120": str(item["body_text"] or "")[:120],
                    "body_chosen": item["body_chosen"],
                }
                for item in intake_items[:10]
            ],
        }

        _write_json(intake_path, intake_items)
        _write_json(summary_path, summary_payload)

        parsed_rows = [
            {
                "message_id": str(item.get("message_id") or ""),
                "subject": str(item.get("subject") or ""),
                "from_addr": str(item.get("from") or ""),
                "parser_confidence": item.get("parser_confidence", item.get("parse_confidence")),
                "parsed": item.get("parsed") if isinstance(item.get("parsed"), dict) else {},
                "parser_errors": (
                    item.get("parser_errors")
                    if isinstance(item.get("parser_errors"), list)
                    else item.get("parse_errors")
                    if isinstance(item.get("parse_errors"), list)
                    else []
                ),
            }
            for item in intake_items
        ]
        _write_jsonl(parsed_emails_path, parsed_rows)

        register_artifact(
            ctx,
            name="gmail_intake_items_json",
            path=intake_path,
            type="json",
            metadata={"count": len(intake_items)},
        )
        register_artifact(
            ctx,
            name="gmail_intake_summary_json",
            path=summary_path,
            type="json",
            metadata={
                "ids_found": ids_found,
                "fetched_count": fetched_count,
                "decoded_plain_count": decoded_plain_count,
                "decoded_html_count": decoded_html_count,
                "decoded_none_count": decoded_none_count,
            },
        )
        register_artifact(
            ctx,
            name="parsed_emails_jsonl",
            path=parsed_emails_path,
            type="jsonl",
            metadata={"count": len(parsed_rows)},
        )

        return StepResult(
            ok=True,
            outputs={
                "ids_found": ids_found,
                "fetched_count": fetched_count,
                "decoded_plain_count": decoded_plain_count,
                "decoded_html_count": decoded_html_count,
                "decoded_none_count": decoded_none_count,
                "artifacts_index": ctx.artifacts_index_path.relative_to(ctx.run_dir).as_posix(),
            },
        )

    def upsert_triage_sheet(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        sheets_cfg = cfg.get("sheets")
        if not isinstance(sheets_cfg, dict):
            return StepResult(ok=False, error="Invalid config: missing sheets section")

        sheet_id = str(sheets_cfg.get("sheet_id") or "").strip()
        if not sheet_id or sheet_id in {"DUMMY_SHEET_ID", "REPLACE_ME"}:
            return StepResult(ok=False, error="Invalid config: missing sheets.sheet_id")

        tabs = sheets_cfg.get("tabs") if isinstance(sheets_cfg.get("tabs"), dict) else {}
        triage_tab = str(tabs.get("triage_tab") or "triage").strip()

        defaults = (
            sheets_cfg.get("defaults") if isinstance(sheets_cfg.get("defaults"), dict) else {}
        )
        default_status = str(defaults.get("status") or "NEW").strip() or "NEW"

        triage_rows = state.data.get("triage_rows")
        if not isinstance(triage_rows, list):
            triage_rows = []

        app_cfg = load_config()
        settings = settings_from_env()
        sheets_svc = build_service(cfg=app_cfg, api="sheets", settings=settings)

        resp = (
            sheets_svc.spreadsheets()
            .values()
            .get(
                spreadsheetId=sheet_id,
                range=f"{triage_tab}!A1:Z",
            )
            .execute()
        )
        existing_values = resp.get("values") if isinstance(resp, dict) else []
        if not isinstance(existing_values, list):
            existing_values = []

        merged_table = upsert_triage_table(
            existing_values=existing_values,
            new_rows=triage_rows,
            default_status=default_status,
            preserve_existing_status=True,
            run_id=ctx.run_id,
        )

        sheets_svc.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{triage_tab}!A1",
            valueInputOption="RAW",
            body={"values": merged_table},
        ).execute()

        export_path = ctx.artifacts_dir / "triage_export.csv"
        export_path.parent.mkdir(parents=True, exist_ok=True)
        with export_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerows(merged_table)

        register_artifact(
            ctx,
            name="triage_export_csv",
            path=export_path,
            type="csv",
            metadata={"rows": max(0, len(merged_table) - 1), "tab": triage_tab},
        )

        preview = merged_table[: min(len(merged_table), 6)]
        log.info(
            "triage_upsert_done",
            sheet_id=sheet_id,
            tab=triage_tab,
            rows_written=max(0, len(merged_table) - 1),
            preview_rows=preview,
        )

        return StepResult(
            ok=True,
            outputs={
                "triage_rows_written": max(0, len(merged_table) - 1),
                "triage_export": export_path.relative_to(ctx.run_dir).as_posix(),
            },
        )

    def process_attachments(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        enabled = _as_bool(state.data.get("attachments_enabled"), False)
        if not enabled:
            return StepResult(
                ok=True,
                outputs={
                    "attachments_total": 0,
                    "attachments_routed": 0,
                    "attachments_quarantined": 0,
                    "attachments_errors": 0,
                    "attachments_enabled": False,
                },
            )

        raw_cfg = state.data.get("attachments_config")
        attachments_cfg = raw_cfg if isinstance(raw_cfg, dict) else {}
        message_ids = state.data.get("message_ids")
        if not isinstance(message_ids, list):
            return StepResult(
                ok=False,
                error="Invalid state: message ids are missing from intake step",
            )

        app_cfg = load_config()
        settings = settings_from_env()
        gmail_service = build_service(cfg=app_cfg, api="gmail", settings=settings)
        adapter = GmailAdapter(service=gmail_service, logger=log, run_id=ctx.run_id)

        route_mode = str(attachments_cfg.get("route_mode") or "artifacts").strip().lower()
        if route_mode not in {"artifacts", "drive"}:
            return StepResult(
                ok=False,
                error="Invalid attachments config: route_mode must be 'artifacts' or 'drive'",
            )

        drive_client = None
        if route_mode == "drive":
            try:
                drive_client = build_service(cfg=app_cfg, api="drive", settings=settings)
            except Exception as exc:
                log.error(
                    "gmail_attachments_drive_client_init_failed",
                    run_id=ctx.run_id,
                    error=str(exc),
                )
                drive_client = None

        raw_dir = ctx.run_dir / "attachments" / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = ctx.run_dir / "attachments" / "manifest.jsonl"
        summary_path = ctx.run_dir / "attachments" / "summary.jsonl"

        total_count = 0
        routed_count = 0
        quarantined_count = 0
        error_count = 0
        summary_rows: list[dict[str, Any]] = []

        for message_id in message_ids:
            if not isinstance(message_id, str):
                continue
            mid = message_id.strip()
            if not mid:
                continue

            try:
                metas = adapter.list_message_attachments(mid)
            except Exception as exc:
                error_count += 1
                summary_rows.append(
                    {
                        "message_id": mid,
                        "status": "ERROR",
                        "reason": f"list_attachments_failed:{exc}",
                    }
                )
                log.error(
                    "gmail_attachment_list_failed",
                    message_id=mid,
                    reason=str(exc),
                )
                continue

            for meta in metas:
                total_count += 1

                safe_filename = _safe_attachment_filename(
                    filename=meta.filename,
                    message_id=meta.message_id,
                    part_id=meta.part_id,
                )
                raw_path = _next_available_file_path(raw_dir, safe_filename)
                try:
                    content = adapter.get_attachment_bytes(
                        message_id=meta.message_id,
                        attachment_id=meta.attachment_id,
                    )
                    raw_path.write_bytes(content)
                except Exception as exc:
                    error_count += 1
                    summary_rows.append(
                        {
                            "message_id": meta.message_id,
                            "filename": meta.filename,
                            "status": "ERROR",
                            "reason": f"download_failed:{exc}",
                        }
                    )
                    log.error(
                        "gmail_attachment_download_failed",
                        message_id=meta.message_id,
                        attachment_id=meta.attachment_id,
                        reason=str(exc),
                    )
                    continue

                validation = validate_attachment(
                    meta=meta, content_bytes=content, cfg=attachments_cfg
                )
                if validation.status == ValidationStatus.INVALID:
                    quarantined = quarantine_attachment(
                        run_dir=ctx.run_dir,
                        meta=meta,
                        content_bytes=content,
                        reason=validation.reason,
                    )
                    if quarantined.status == "quarantined":
                        quarantined_count += 1
                    else:
                        error_count += 1
                    summary_rows.append(
                        {
                            "message_id": meta.message_id,
                            "filename": meta.filename,
                            "status": quarantined.status,
                            "reason": quarantined.reason,
                            "saved_path": quarantined.saved_path or "",
                        }
                    )
                    continue

                routed = route_attachment(
                    run_dir=ctx.run_dir,
                    meta=meta,
                    content_bytes=content,
                    cfg=attachments_cfg,
                    drive_client=drive_client,
                )
                if routed.status.startswith("routed_"):
                    routed_count += 1
                else:
                    error_count += 1

                summary_rows.append(
                    {
                        "message_id": meta.message_id,
                        "filename": meta.filename,
                        "status": routed.status,
                        "reason": routed.reason,
                        "saved_path": routed.saved_path or "",
                        "drive_file_id": routed.drive_file_id or "",
                        "drive_file_url": routed.drive_file_url or "",
                    }
                )

        if summary_rows:
            _write_jsonl_append(summary_path, summary_rows)

        log.info(
            "gmail_attachments_summary",
            run_id=ctx.run_id,
            total=total_count,
            routed=routed_count,
            quarantined=quarantined_count,
            errors=error_count,
            manifest_exists=manifest_path.exists(),
        )

        if manifest_path.exists():
            register_artifact(
                ctx,
                name="attachments_manifest_jsonl",
                path=manifest_path,
                type="jsonl",
                metadata={
                    "total": total_count,
                    "routed": routed_count,
                    "quarantined": quarantined_count,
                    "errors": error_count,
                },
            )

        if summary_path.exists():
            register_artifact(
                ctx,
                name="attachments_summary_jsonl",
                path=summary_path,
                type="jsonl",
                metadata={
                    "total": total_count,
                    "routed": routed_count,
                    "quarantined": quarantined_count,
                    "errors": error_count,
                },
            )

        return StepResult(
            ok=True,
            outputs={
                "attachments_total": total_count,
                "attachments_routed": routed_count,
                "attachments_quarantined": quarantined_count,
                "attachments_errors": error_count,
                "attachments_route_mode": route_mode,
                "attachments_manifest": manifest_path.relative_to(ctx.run_dir).as_posix(),
                "attachments_summary": summary_path.relative_to(ctx.run_dir).as_posix(),
            },
        )

    def apply_actions(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        raw_action_items = state.data.get("action_items")
        action_items: list[ActionItem] = []
        if isinstance(raw_action_items, list):
            for item in raw_action_items:
                if not isinstance(item, dict):
                    continue
                message_id = str(item.get("message_id") or "")
                parse_ok = bool(item.get("parse_ok"))
                try:
                    confidence = float(item.get("confidence", 0.0))
                except (TypeError, ValueError):
                    confidence = 0.0
                error_count_raw = item.get("error_count")
                if not isinstance(error_count_raw, int):
                    try:
                        error_count_raw = int(error_count_raw)
                    except (TypeError, ValueError):
                        error_count_raw = 0
                error_count = int(error_count_raw)

                action_items.append(
                    ActionItem(
                        message_id=message_id,
                        parse_ok=parse_ok,
                        error_count=error_count,
                        confidence=confidence,
                    )
                )

        min_confidence = _as_float(state.data.get("gmail_min_confidence"), 0.6)
        archive_on_success = _as_bool(state.data.get("gmail_archive_on_success"), False)
        archive_on_failure = _as_bool(state.data.get("gmail_archive_on_failure"), False)
        success_label_name = str(state.data.get("gmail_success_label_name") or "").strip()
        needs_review_label_name = str(state.data.get("gmail_needs_review_label_name") or "").strip()
        error_label_name = str(state.data.get("gmail_error_label_name") or "").strip()

        if not success_label_name or not needs_review_label_name or not error_label_name:
            return StepResult(
                ok=False,
                error="Invalid state: missing configured Gmail label names",
            )

        app_cfg = load_config()
        settings = settings_from_env()
        gmail_service = build_service(cfg=app_cfg, api="gmail", settings=settings)
        adapter = GmailAdapter(service=gmail_service, logger=log, run_id=ctx.run_id)

        success_label_id = adapter.ensure_label(success_label_name)
        needs_review_label_id = adapter.ensure_label(needs_review_label_name)
        error_label_id = adapter.ensure_label(error_label_name)

        plan = build_action_plan(action_items, min_confidence=min_confidence)
        summary = summarize_plan(plan)

        log.info(
            "action_plan_built",
            workflow=name,
            run_id=ctx.run_id,
            success_count=summary.get("success_count", 0),
            needs_review_count=summary.get("needs_review_count", 0),
            min_confidence=min_confidence,
            archive_on_success=archive_on_success,
            archive_on_failure=archive_on_failure,
            min_confidence_threshold=min_confidence,
            error_label_id=error_label_id,
        )

        success_ids = plan.get("success", [])
        needs_review_ids = plan.get("needs_review", [])

        if success_ids:
            remove = []
            if archive_on_success:
                remove.append("INBOX")
            adapter.batch_modify(
                message_ids=success_ids,
                add_label_ids=[success_label_id],
                remove_label_ids=remove,
            )

        if needs_review_ids:
            remove = []
            if archive_on_failure:
                remove.append("INBOX")
            adapter.batch_modify(
                message_ids=needs_review_ids,
                add_label_ids=[needs_review_label_id],
                remove_label_ids=remove,
            )

        archived_success_count = len(success_ids) if archive_on_success else 0
        archived_failure_count = len(needs_review_ids) if archive_on_failure else 0

        actions_plan = {
            "plan": plan,
            "config": {
                "min_confidence": min_confidence,
                "archive_on_success": archive_on_success,
                "archive_on_failure": archive_on_failure,
                "success_label": success_label_name,
                "needs_review_label": needs_review_label_name,
                "error_label": error_label_name,
            },
            "totals": summary,
        }
        actions_applied = {
            "actions_success_count": summary.get("success_count", 0),
            "actions_needs_review_count": summary.get("needs_review_count", 0),
            "archived_success_count": archived_success_count,
            "archived_failure_count": archived_failure_count,
            "archive_on_success": archive_on_success,
            "archive_on_failure": archive_on_failure,
        }

        actions_plan_path = ctx.artifacts_dir / "actions_plan.json"
        actions_applied_path = ctx.artifacts_dir / "actions_applied.json"
        _write_json(actions_plan_path, actions_plan)
        _write_json(actions_applied_path, actions_applied)

        register_artifact(
            ctx,
            name="actions_plan_json",
            path=actions_plan_path,
            type="json",
            metadata=actions_applied,
        )
        register_artifact(
            ctx,
            name="actions_applied_json",
            path=actions_applied_path,
            type="json",
            metadata=actions_applied,
        )

        log.info(
            "gmail_actions_applied",
            workflow=name,
            run_id=ctx.run_id,
            actions_success_count=summary.get("success_count", 0),
            actions_needs_review_count=summary.get("needs_review_count", 0),
            archived_success_count=archived_success_count,
            archived_failure_count=archived_failure_count,
        )

        log.info(
            "apply_actions_done",
            run_id=ctx.run_id,
            workflow=name,
            actions_success_count=summary.get("success_count", 0),
            actions_needs_review_count=summary.get("needs_review_count", 0),
            archived_success_count=archived_success_count,
            archived_failure_count=archived_failure_count,
            archive_on_success=archive_on_success,
            archive_on_failure=archive_on_failure,
            actions_plan_path=actions_plan_path.relative_to(ctx.run_dir).as_posix(),
            actions_applied_path=actions_applied_path.relative_to(ctx.run_dir).as_posix(),
        )

        return StepResult(
            ok=True,
            outputs={
                "actions_success_count": summary.get("success_count", 0),
                "actions_needs_review_count": summary.get("needs_review_count", 0),
                "archived_success_count": archived_success_count,
                "archived_failure_count": archived_failure_count,
                "actions_plan": actions_plan_path.relative_to(ctx.run_dir).as_posix(),
                "actions_applied": actions_applied_path.relative_to(ctx.run_dir).as_posix(),
            },
        )

    steps = [
        Step(name="validate_config", fn=validate_config),
        Step(name="collect_intake", fn=collect_intake),
        Step(name="upsert_triage_sheet", fn=upsert_triage_sheet),
        Step(name="attachments", fn=process_attachments),
        Step(name="apply_actions", fn=apply_actions),
    ]
    return Workflow(name=name, steps=steps)


_register("gmail_to_sheets_intake", get_workflow)
