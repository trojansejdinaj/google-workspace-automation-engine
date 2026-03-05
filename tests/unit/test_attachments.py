from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from gw_engine.attachments import (
    QuarantineResult,
    RouteMode,
    RouteResult,
    ValidationStatus,
    quarantine_attachment,
    route_attachment,
    validate_attachment,
)
from gw_engine.gmail_adapter import AttachmentMeta


def _meta(filename: str, mime: str, attachment_id: str = "a1") -> AttachmentMeta:
    return AttachmentMeta(
        filename=filename,
        mime_type=mime,
        size_estimate=None,
        attachment_id=attachment_id,
        part_id=None,
        message_id="m1",
    )


def test_validate_attachment_rejects_oversize_attachment() -> None:
    result = validate_attachment(
        meta=_meta("big.bin", "application/octet-stream", "a1"),
        content_bytes=b"x" * 11,
        cfg={"max_size_bytes": 10, "allowed_mime_types": ["application/octet-stream"]},
    )

    assert result.status == ValidationStatus.INVALID
    assert result.reason.startswith("size_exceeds_limit")


def test_validate_attachment_mime_or_extension_match_passes(tmp_path: Path) -> None:
    result_pdf_by_ext = validate_attachment(
        meta=_meta("report.pdf", "application/octet-stream", "a1"),
        content_bytes=b"abc",
        cfg={"allowed_mime_types": ["text/plain"], "allowed_extensions": [".pdf"]},
    )
    assert result_pdf_by_ext.status == ValidationStatus.VALID

    result_txt_by_mime = validate_attachment(
        meta=_meta("report.txt", "text/plain", "a2"),
        content_bytes=b"abc",
        cfg={"allowed_mime_types": ["text/plain"], "allowed_extensions": [".pdf"]},
    )
    assert result_txt_by_mime.status == ValidationStatus.VALID

    result_blocked = validate_attachment(
        meta=_meta("report.exe", "application/x-msdownload", "a3"),
        content_bytes=b"abc",
        cfg={"allowed_mime_types": ["text/plain"], "allowed_extensions": [".pdf"]},
    )
    assert result_blocked.status == ValidationStatus.INVALID


def test_quarantine_attachment_writes_file_and_manifest(tmp_path: Path) -> None:
    run_dir = tmp_path / "run1"
    result = quarantine_attachment(
        run_dir=run_dir,
        meta=_meta("dangerous.exe", "application/octet-stream", "a1"),
        content_bytes=b"bad",
        reason="policy_blocked",
    )

    assert isinstance(result, QuarantineResult)
    assert result.status == "quarantined"
    assert result.saved_path is not None
    assert Path(result.saved_path).exists()
    assert Path(result.saved_path).read_bytes() == b"bad"

    manifest_path = run_dir / "attachments" / "manifest.jsonl"
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["status"] == "quarantined"
    assert payload["reason"] == "policy_blocked"


def test_route_attachment_saves_artifacts_when_configured(tmp_path: Path) -> None:
    run_dir = tmp_path / "run2"
    result = route_attachment(
        run_dir=run_dir,
        meta=_meta("invoice.pdf", "application/pdf", "a1"),
        content_bytes=b"invoice",
        cfg={"route_mode": RouteMode.ARTIFACTS.value},
    )

    assert isinstance(result, RouteResult)
    assert result.status == "routed_artifacts"
    assert result.saved_path is not None
    assert Path(result.saved_path).exists()
    assert Path(result.saved_path).read_bytes() == b"invoice"


def test_route_attachment_uploads_to_drive_with_mock_client(tmp_path: Path) -> None:
    drive_client = MagicMock()
    drive_client.files.return_value.create.return_value.execute.return_value = {
        "id": "drive-id-1",
        "webViewLink": "https://drive.google.com/file/d/drive-id-1/view",
    }

    run_dir = tmp_path / "run3"
    result = route_attachment(
        run_dir=run_dir,
        meta=_meta("diagram.png", "image/png", "a1"),
        content_bytes=b"png",
        cfg={"route_mode": RouteMode.DRIVE.value, "drive_folder_id": "folder-id"},
        drive_client=drive_client,
    )

    assert result.status == "routed_drive"
    assert result.drive_file_id == "drive-id-1"
    assert result.drive_file_url == "https://drive.google.com/file/d/drive-id-1/view"
    assert result.saved_path is None


def test_validate_attachment_accepts_when_allowlist_empty(tmp_path: Path) -> None:
    result = validate_attachment(
        meta=_meta("anything.bin", "application/octet-stream", "a1"),
        content_bytes=b"abc",
        cfg={"max_size_bytes": 1024},
    )

    assert result.status == ValidationStatus.VALID
