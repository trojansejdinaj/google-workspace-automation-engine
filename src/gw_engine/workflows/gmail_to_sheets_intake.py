from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gw_engine.artifacts import register_artifact
from gw_engine.clients import build_service, settings_from_env
from gw_engine.config import load_config
from gw_engine.contracts import RunState, Step, StepResult, Workflow
from gw_engine.gmail_adapter import GmailAdapter
from gw_engine.gmail_decode import decode_message_bodies
from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext
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


def get_workflow(cfg: dict[str, Any]) -> Workflow:
    name = "gmail_to_sheets_intake"

    def validate_config(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        gmail_cfg = cfg.get("gmail")
        if not isinstance(gmail_cfg, dict):
            return StepResult(ok=False, error="Invalid config: missing gmail section")

        query = str(gmail_cfg.get("gmail_query") or "").strip()
        if not query:
            return StepResult(ok=False, error="Invalid config: missing gmail.gmail_query")

        options_cfg = cfg.get("options")
        options_map = options_cfg if isinstance(options_cfg, dict) else {}
        max_messages = max(1, _as_int(options_map.get("max_messages"), 50))

        state.data["gmail_query"] = query
        state.data["max_messages"] = max_messages

        log.info(
            "config_valid",
            workflow=name,
            query=query,
            max_messages=max_messages,
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

        decoded_plain_count = 0
        decoded_html_count = 0
        decoded_none_count = 0

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

            body_text = str(decoded.get("text") or "")
            warnings_any = decoded.get("warnings")
            warnings = (
                [str(w) for w in warnings_any]
                if isinstance(warnings_any, list)
                else [str(warnings_any)]
                if warnings_any is not None
                else []
            )

            intake_items.append(
                {
                    "message_id": str(message.get("id") or ""),
                    "thread_id": str(message.get("threadId") or ""),
                    "internal_date": str(message.get("internalDate") or ""),
                    "from": _header_value(message, "From"),
                    "to": _header_value(message, "To"),
                    "subject": _header_value(message, "Subject"),
                    "date": _header_value(message, "Date"),
                    "body_text": body_text,
                    "body_chosen": chosen,
                    "decode_warnings": warnings,
                }
            )

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

    steps = [
        Step(name="validate_config", fn=validate_config),
        Step(name="collect_intake", fn=collect_intake),
    ]
    return Workflow(name=name, steps=steps)


_register("gmail_to_sheets_intake", get_workflow)
