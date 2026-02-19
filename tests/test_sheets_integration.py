from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from gw_engine.clients import build_service, settings_from_env
from gw_engine.config import ConfigError, load_config
from tests.integration_helpers import require_google_sheets_integration_env


@pytest.mark.integration
def test_sheets_write_then_read_roundtrip() -> None:
    sheet_id = require_google_sheets_integration_env()

    try:
        cfg = load_config()
    except ConfigError as exc:
        pytest.skip(f"Config unavailable for integration test: {exc}")

    sheets = build_service(cfg=cfg, api="sheets", settings=settings_from_env())

    tab_name = "_gw_engine_itest"
    cell_range = f"{tab_name}!A1"
    unique_value = f"gw-itest-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-{uuid4().hex[:8]}"

    # Ensure dedicated integration tab exists.
    ss = sheets.spreadsheets().get(spreadsheetId=sheet_id).execute()
    existing = {s["properties"]["title"] for s in ss.get("sheets", [])}
    if tab_name not in existing:
        sheets.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]},
        ).execute()

    sheets.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=cell_range,
        valueInputOption="RAW",
        body={"values": [[unique_value]]},
    ).execute()

    got_values = (
        sheets.spreadsheets().values().get(spreadsheetId=sheet_id, range=cell_range).execute()
    ).get("values", [[""]])
    got = got_values[0][0] if got_values and got_values[0] else ""
    assert got == unique_value

    # Best-effort cleanup: clear the test cell.
    try:
        sheets.spreadsheets().values().clear(
            spreadsheetId=sheet_id,
            range=cell_range,
            body={},
        ).execute()
    except Exception:
        pass
