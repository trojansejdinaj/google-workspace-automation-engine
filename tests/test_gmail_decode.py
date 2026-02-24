from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import pytest

from gw_engine.gmail_decode import decode_message_bodies


def _b64url(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("ascii").rstrip("=")


def _fixture_files() -> list[Path]:
    fixture_dir = Path("tests/fixtures/gmail")
    if not fixture_dir.exists():
        return []
    return sorted(
        p for p in fixture_dir.glob("msg_*.json") if p.is_file() and p.name != "_index.json"
    )


def test_decode_message_bodies_from_gmail_fixtures() -> None:
    fixtures = _fixture_files()
    if not fixtures:
        pytest.skip("No Gmail fixtures found under tests/fixtures/gmail")

    for fixture in fixtures:
        msg = json.loads(fixture.read_text(encoding="utf-8"))
        decoded = decode_message_bodies(msg)

        assert decoded["chosen"] in {"plain", "html", "none"}
        assert isinstance(decoded["warnings"], list)

        if decoded["chosen"] != "none":
            assert len(decoded["text"]) > 0


def test_decode_message_bodies_payload_body_data_plain_text() -> None:
    message = {
        "id": "m1",
        "payload": {
            "mimeType": "text/plain",
            "body": {"data": _b64url("hello plain")},
            "headers": [],
        },
    }

    decoded = decode_message_bodies(message)

    assert decoded["chosen"] == "plain"
    assert decoded["text_plain"] == "hello plain"
    assert decoded["text"] == "hello plain"
    assert isinstance(decoded["warnings"], list)


def test_decode_message_bodies_multipart_alternative_prefers_plain() -> None:
    message = {
        "id": "m2",
        "payload": {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64url("plain body")}},
                {"mimeType": "text/html", "body": {"data": _b64url("<p>html body</p>")}},
            ],
        },
    }

    decoded = decode_message_bodies(message)

    assert decoded["chosen"] == "plain"
    assert decoded["text"] == "plain body"
    assert decoded["text_html"] == "<p>html body</p>"


def test_decode_message_bodies_fallback_to_html_when_plain_empty() -> None:
    message = {
        "id": "m2b",
        "payload": {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64url("   ")}},
                {
                    "mimeType": "text/html",
                    "body": {"data": _b64url("<div><b>html fallback</b></div>")},
                },
            ],
        },
    }

    decoded = decode_message_bodies(message)

    assert decoded["chosen"] == "html"
    assert decoded["text"] == "<div><b>html fallback</b></div>"
    assert decoded["text_plain"] == "   "
    assert decoded["text_html"] == "<div><b>html fallback</b></div>"


def test_decode_message_bodies_missing_payload_returns_none() -> None:
    decoded = decode_message_bodies({"id": "m3"})

    assert decoded["chosen"] == "none"
    assert decoded["text"] == ""
    assert decoded["text_plain"] is None
    assert decoded["text_html"] is None
    assert decoded["warnings"] == []


def test_decode_message_bodies_invalid_base64_adds_warning_no_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_invalid(data: str) -> bytes:  # noqa: ARG001
        raise ValueError("invalid base64url test")

    monkeypatch.setattr("gw_engine.gmail_decode.safe_base64url_decode", _raise_invalid)

    message: dict[str, Any] = {
        "id": "m4",
        "payload": {
            "mimeType": "text/plain",
            "body": {"data": "not-really-base64"},
        },
    }

    decoded = decode_message_bodies(message)

    assert decoded["chosen"] == "none"
    assert decoded["text"] == ""
    assert isinstance(decoded["warnings"], list)
    assert len(decoded["warnings"]) >= 1
