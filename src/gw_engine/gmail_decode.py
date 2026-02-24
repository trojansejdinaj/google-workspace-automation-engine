from __future__ import annotations

import base64
from typing import Any


def safe_base64url_decode(data: str) -> bytes:
    if not isinstance(data, str):
        raise ValueError("invalid base64url data: expected string")

    normalized = data.strip()
    if normalized == "":
        return b""

    padding = (-len(normalized)) % 4
    normalized += "=" * padding

    try:
        return base64.urlsafe_b64decode(normalized)
    except Exception as exc:
        context = data[:24].replace("\n", " ").replace("\r", " ")
        raise ValueError(f"invalid base64url data near {context!r}") from exc


def extract_parts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("malformed payload: expected dict")

    parts: list[dict[str, Any]] = []

    def walk(part: dict[str, Any]) -> None:
        if not isinstance(part, dict):
            raise ValueError("malformed MIME part: expected dict")

        parts.append(part)

        children = part.get("parts")
        if children is None:
            return
        if not isinstance(children, list):
            raise ValueError("malformed MIME structure: parts must be a list")

        for child in children:
            if not isinstance(child, dict):
                raise ValueError("malformed MIME structure: part entry must be a dict")
            walk(child)

    walk(payload)
    return parts


def decode_message_bodies(message: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(message, dict):
        raise ValueError("malformed message: expected dict")

    warnings: list[str] = []

    payload = message.get("payload")
    if payload is None:
        return {
            "text_plain": None,
            "text_html": None,
            "chosen": "none",
            "text": "",
            "warnings": warnings,
        }
    if not isinstance(payload, dict):
        raise ValueError("malformed message payload: expected dict")

    plain_chunks: list[str] = []
    html_chunks: list[str] = []

    for part in extract_parts(payload):
        body = part.get("body")
        if body is None:
            continue
        if not isinstance(body, dict):
            raise ValueError("malformed body: expected dict")

        data = body.get("data")
        if data is None:
            continue
        if not isinstance(data, str):
            raise ValueError("malformed body data: expected string")

        mime_type = str(part.get("mimeType") or "")

        try:
            text = safe_base64url_decode(data).decode("utf-8", errors="replace")
        except ValueError as exc:
            warnings.append(str(exc))
            continue

        if mime_type == "text/plain":
            plain_chunks.append(text)
        elif mime_type == "text/html":
            html_chunks.append(text)
        elif mime_type == "":
            # Top-level payload.body.data can exist without explicit mimeType in edge responses.
            plain_chunks.append(text)

    text_plain = "\n\n".join(plain_chunks) if plain_chunks else None
    text_html = "\n\n".join(html_chunks) if html_chunks else None

    plain_non_empty = bool(text_plain and text_plain.strip())
    html_non_empty = bool(text_html and text_html.strip())

    if plain_non_empty:
        chosen = "plain"
        text = text_plain or ""
    elif html_non_empty:
        chosen = "html"
        text = text_html or ""
    else:
        chosen = "none"
        text = ""

    return {
        "text_plain": text_plain,
        "text_html": text_html,
        "chosen": chosen,
        "text": text,
        "warnings": warnings,
    }
