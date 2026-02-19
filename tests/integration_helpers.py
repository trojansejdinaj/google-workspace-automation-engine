from __future__ import annotations

import os
from pathlib import Path

import pytest


def require_google_sheets_integration_env() -> str:
    """
    Returns GW_TEST_SHEET_ID when integration env is available.
    Otherwise skips the test with an informative reason.

    Supported auth env combinations:
    - Service account: GOOGLE_SERVICE_ACCOUNT_JSON (must exist)
    - OAuth user creds: GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET + GOOGLE_REFRESH_TOKEN
    """
    env = os.environ
    sheet_id = (env.get("GW_TEST_SHEET_ID") or "").strip()
    if not sheet_id:
        pytest.skip("Missing GW_TEST_SHEET_ID; skipping Google Sheets integration test")

    sa_path = (env.get("GOOGLE_SERVICE_ACCOUNT_JSON") or "").strip()
    has_service_account = bool(sa_path)
    has_oauth = all(
        [
            (env.get("GOOGLE_CLIENT_ID") or "").strip(),
            (env.get("GOOGLE_CLIENT_SECRET") or "").strip(),
            (env.get("GOOGLE_REFRESH_TOKEN") or "").strip(),
        ]
    )

    if not has_service_account and not has_oauth:
        pytest.skip(
            "Missing Google auth env vars; set GOOGLE_SERVICE_ACCOUNT_JSON or "
            "GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET/GOOGLE_REFRESH_TOKEN"
        )

    if has_service_account and not Path(sa_path).exists():
        pytest.skip(f"GOOGLE_SERVICE_ACCOUNT_JSON path does not exist: {sa_path}")

    return sheet_id
