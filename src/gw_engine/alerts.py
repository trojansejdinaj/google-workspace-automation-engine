from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gw_engine.artifacts import register_artifact
from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext


def build_triage_sheet_url(sheet_id: str, triage_tab: str) -> str:
    base = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    clean_tab = triage_tab.strip()
    return f"{base}#gid={clean_tab}" if clean_tab else base


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    tmp.replace(path)


def emit_needs_review_alert(
    ctx: RunContext,
    log: JsonlLogger,
    *,
    workflow: str,
    sheet_id: str,
    triage_tab: str,
    new_count: int,
    total_count: int | None = None,
) -> dict[str, Any]:
    triage_sheet_url = build_triage_sheet_url(sheet_id=sheet_id, triage_tab=triage_tab)
    base_payload: dict[str, Any] = {
        "workflow": workflow,
        "sheet_id": sheet_id,
        "triage_tab": triage_tab,
        "triage_sheet_url": triage_sheet_url,
        "new_needs_review_count": new_count,
        "total_needs_review_count": total_count,
    }

    if new_count == 0:
        log.info(
            "needs_review_alert_suppressed",
            run_id=ctx.run_id,
            workflow=workflow,
            new_needs_review_count=new_count,
            total_needs_review_count=total_count,
            triage_sheet_url=triage_sheet_url,
        )
        return {"emitted": False, **base_payload}

    alert_path = ctx.artifacts_dir / "needs_review_alert.json"
    _write_json(alert_path, base_payload)
    artifact = register_artifact(
        ctx,
        name="needs_review_alert_json",
        path=alert_path,
        type="json",
        metadata=base_payload,
    )

    log.info(
        "needs_review_alert_emitted",
        run_id=ctx.run_id,
        workflow=workflow,
        new_needs_review_count=new_count,
        total_needs_review_count=total_count,
        triage_sheet_url=triage_sheet_url,
        alert_artifact=artifact.path,
    )
    return {"emitted": True, **base_payload, "artifact": artifact.path}
