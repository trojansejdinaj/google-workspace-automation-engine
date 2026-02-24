from __future__ import annotations

import os

import pytest

from gw_engine.clients import build_service, settings_from_env
from gw_engine.config import load_config
from gw_engine.gmail_adapter import GmailAdapter
from gw_engine.gmail_decode import decode_message_bodies
from gw_engine.logger import JsonlLogger


@pytest.mark.integration
def test_gmail_adapter_search_fetch_decode_integration(tmp_path) -> None:  # type: ignore[no-untyped-def]
    enabled = (os.environ.get("GW_GMAIL_INTEGRATION") or "").strip()
    if enabled != "1":
        pytest.skip("Set GW_GMAIL_INTEGRATION=1 to enable Gmail integration test")

    query = (os.environ.get("GW_GMAIL_QUERY") or "").strip()
    if not query:
        pytest.skip("Set GW_GMAIL_QUERY to a Gmail search query for integration testing")

    cfg = load_config()
    settings = settings_from_env()
    service = build_service(cfg=cfg, api="gmail", settings=settings)

    log = JsonlLogger(path=tmp_path / "gmail_integration.log.jsonl", component="test")
    adapter = GmailAdapter(service=service, logger=log, run_id="it-gmail")

    ids = adapter.search_message_ids(query=query, max_results=1)
    if not ids:
        pytest.skip(f"No messages found for query: {query}")

    messages = adapter.fetch_messages(ids, format="full")
    assert len(messages) >= 1

    decoded = decode_message_bodies(messages[0])
    assert decoded["chosen"] in {"plain", "html", "none"}
    assert isinstance(decoded["warnings"], list)
