from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from gw_engine.gmail_adapter import AttachmentMeta, GmailAdapter
from gw_engine.logger import JsonlLogger

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "gmail"


def _load_fixture(filename: str) -> dict[str, Any]:
    fixture = _FIXTURE_DIR / filename
    return json.loads(fixture.read_text(encoding="utf-8"))


def test_list_message_attachments_with_no_attachments(tmp_path: Path) -> None:
    service = MagicMock()
    service.users.return_value.messages.return_value.get.return_value.execute.return_value = (
        _load_fixture("msg_zero_attachments.json")
    )

    logger = JsonlLogger(path=tmp_path / "gmail_adapter_attachments.log.jsonl", component="test")
    adapter = GmailAdapter(service=service, logger=logger, run_id="run-attach-0")
    attachments = adapter.list_message_attachments("msg-zero")

    assert attachments == []
    service.users.return_value.messages.return_value.get.assert_called_once_with(
        userId="me",
        id="msg-zero",
        format="full",
    )


def test_list_message_attachments_collects_nested_multipart_attachments(tmp_path: Path) -> None:
    service = MagicMock()
    service.users.return_value.messages.return_value.get.return_value.execute.return_value = (
        _load_fixture("msg_nested_multipart_attachments.json")
    )

    logger = JsonlLogger(
        path=tmp_path / "gmail_adapter_attachments_nested.log.jsonl", component="test"
    )
    adapter = GmailAdapter(service=service, logger=logger, run_id="run-attach-2")
    attachments = adapter.list_message_attachments("msg-nested")

    assert len(attachments) == 2
    assert attachments == [
        AttachmentMeta(
            filename="invoice_42.pdf",
            mime_type="application/pdf",
            size_estimate=1024,
            attachment_id="ATTACH_PDF",
            part_id="1.1",
            message_id="msg-nested",
        ),
        AttachmentMeta(
            filename="diagram.png",
            mime_type="image/png",
            size_estimate=2048,
            attachment_id="ATTACH_PNG",
            part_id="1.2",
            message_id="msg-nested",
        ),
    ]
    service.users.return_value.messages.return_value.get.assert_called_once_with(
        userId="me",
        id="msg-nested",
        format="full",
    )


def test_get_attachment_bytes_decodes_base64url_payload(tmp_path: Path) -> None:
    expected_bytes = b"%PDF-FAKE-DATA%"
    encoded = base64.urlsafe_b64encode(expected_bytes).decode("ascii").rstrip("=")

    service = MagicMock()
    service.users.return_value.messages.return_value.attachments.return_value.get.return_value.execute.return_value = {
        "data": encoded
    }

    logger = JsonlLogger(
        path=tmp_path / "gmail_adapter_attachments_download.log.jsonl", component="test"
    )
    adapter = GmailAdapter(service=service, logger=logger, run_id="run-attach-dl")
    payload = adapter.get_attachment_bytes("msg-bytes", "ATTACH_BYTES")

    assert payload == expected_bytes
    service.users.return_value.messages.return_value.attachments.return_value.get.assert_called_once_with(
        userId="me",
        messageId="msg-bytes",
        id="ATTACH_BYTES",
    )
