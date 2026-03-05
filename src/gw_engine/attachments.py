from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from gw_engine.gmail_adapter import AttachmentMeta


class ValidationStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"


class RouteMode(str, Enum):
    ARTIFACTS = "artifacts"
    DRIVE = "drive"


@dataclass(frozen=True)
class ValidationResult:
    status: ValidationStatus
    reason: str


@dataclass(frozen=True)
class QuarantineResult:
    status: str
    reason: str
    manifest_entry: dict[str, Any]
    saved_path: str | None = None


@dataclass(frozen=True)
class RouteResult:
    status: str
    reason: str
    manifest_entry: dict[str, Any]
    saved_path: str | None = None
    drive_file_id: str | None = None
    drive_file_url: str | None = None


def validate_attachment(
    meta: AttachmentMeta,
    content_bytes: bytes,
    cfg: dict[str, Any],
) -> ValidationResult:
    size_limit = _coerce_int(cfg.get("max_size_bytes"))
    if size_limit is not None and len(content_bytes) > size_limit:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason=f"size_exceeds_limit:{len(content_bytes)}>{size_limit}",
        )

    allowed_mime_types = _normalize_lower_set(cfg.get("allowed_mime_types"))
    allowed_extensions = _normalize_lower_set(cfg.get("allowed_extensions"))

    if not allowed_mime_types and not allowed_extensions:
        return ValidationResult(status=ValidationStatus.VALID, reason="ok")

    mime = (meta.mime_type or "").strip().lower()
    ext = Path(meta.filename or "").suffix.strip().lower()

    mime_ok = not allowed_mime_types or (mime in allowed_mime_types)
    ext_ok = not allowed_extensions or (ext in allowed_extensions)
    if mime_ok or ext_ok:
        return ValidationResult(status=ValidationStatus.VALID, reason="ok")

    return ValidationResult(
        status=ValidationStatus.INVALID,
        reason=f"policy_blocked:mime={mime or '?'}|ext={ext or '?'}",
    )


def quarantine_attachment(
    run_dir: Path,
    meta: AttachmentMeta,
    content_bytes: bytes,
    reason: str,
) -> QuarantineResult:
    try:
        sha256_hex = _sha256_hex(content_bytes)
        filename = _safe_filename(meta.filename, meta.message_id, meta.part_id)
        quarantine_dir = _attachments_dir(run_dir, "quarantine")
        saved_path = _next_available_path(quarantine_dir, filename)

        saved_path.write_bytes(content_bytes)

        manifest_entry = _manifest_entry(
            meta=meta,
            size=len(content_bytes),
            sha256=sha256_hex,
            status="quarantined",
            reason=reason,
            saved_path=saved_path,
        )
        _append_manifest(_manifest_path(run_dir), manifest_entry)
        return QuarantineResult(
            status="quarantined",
            reason=reason,
            manifest_entry=manifest_entry,
            saved_path=str(saved_path),
        )
    except Exception as exc:
        sha256_hex = _sha256_hex(content_bytes)
        manifest_entry = _manifest_entry(
            meta=meta,
            size=len(content_bytes),
            sha256=sha256_hex,
            status="error",
            reason=f"quarantine_error:{exc}",
            saved_path=None,
        )
        _append_manifest(_manifest_path(run_dir), manifest_entry)
        return QuarantineResult(
            status="error",
            reason=f"quarantine_error:{exc}",
            manifest_entry=manifest_entry,
            saved_path=None,
        )


def route_attachment(
    run_dir: Path,
    meta: AttachmentMeta,
    content_bytes: bytes,
    cfg: dict[str, Any],
    drive_client: Any | None = None,
) -> RouteResult:
    mode = str(cfg.get("route_mode") or RouteMode.ARTIFACTS.value).strip().lower()
    if mode not in {RouteMode.ARTIFACTS.value, RouteMode.DRIVE.value}:
        mode = RouteMode.ARTIFACTS.value

    sha256_hex = _sha256_hex(content_bytes)
    filename = _safe_filename(meta.filename, meta.message_id, meta.part_id)
    manifest_path = _manifest_path(run_dir)

    if mode == RouteMode.ARTIFACTS.value:
        try:
            routed_dir = _attachments_dir(run_dir, "routed")
            saved_path = _next_available_path(routed_dir, filename)
            saved_path.write_bytes(content_bytes)
            manifest_entry = _manifest_entry(
                meta=meta,
                size=len(content_bytes),
                sha256=sha256_hex,
                status="routed_artifacts",
                reason="ok",
                saved_path=saved_path,
            )
            _append_manifest(manifest_path, manifest_entry)
            return RouteResult(
                status="routed_artifacts",
                reason="ok",
                manifest_entry=manifest_entry,
                saved_path=str(saved_path),
            )
        except Exception as exc:
            manifest_entry = _manifest_entry(
                meta=meta,
                size=len(content_bytes),
                sha256=sha256_hex,
                status="error",
                reason=f"route_error:{exc}",
                saved_path=None,
            )
            _append_manifest(manifest_path, manifest_entry)
            return RouteResult(
                status="error",
                reason=f"route_error:{exc}",
                manifest_entry=manifest_entry,
            )

    if mode == RouteMode.DRIVE.value:
        drive_folder_id = str(cfg.get("drive_folder_id") or "").strip()
        if not drive_folder_id:
            reason = "drive_missing_folder_id"
            manifest_entry = _manifest_entry(
                meta=meta,
                size=len(content_bytes),
                sha256=sha256_hex,
                status="error",
                reason=reason,
                saved_path=None,
            )
            _append_manifest(manifest_path, manifest_entry)
            return RouteResult(
                status="error",
                reason=reason,
                manifest_entry=manifest_entry,
            )

        if drive_client is None:
            reason = "drive_client_not_configured"
            manifest_entry = _manifest_entry(
                meta=meta,
                size=len(content_bytes),
                sha256=sha256_hex,
                status="error",
                reason=reason,
                saved_path=None,
            )
            _append_manifest(manifest_path, manifest_entry)
            return RouteResult(
                status="error",
                reason=reason,
                manifest_entry=manifest_entry,
            )

        try:
            from googleapiclient.http import MediaInMemoryUpload

            media = MediaInMemoryUpload(
                content_bytes,
                mimetype=meta.mime_type or "application/octet-stream",
                resumable=False,
            )
            response = (
                drive_client.files()
                .create(
                    body={"name": filename, "parents": [drive_folder_id]},
                    media_body=media,
                    fields="id,webViewLink,webContentLink",
                )
                .execute()
            )
            if not isinstance(response, dict):
                raise RuntimeError("drive upload returned non-dict response")

            drive_file_id = str(response.get("id")) if isinstance(response.get("id"), str) else None
            drive_file_url = response.get("webViewLink") or response.get("webContentLink")

            manifest_entry = _manifest_entry(
                meta=meta,
                size=len(content_bytes),
                sha256=sha256_hex,
                status="routed_drive",
                reason="ok",
                saved_path=None,
                drive_file_id=drive_file_id,
                drive_file_url=drive_file_url,
            )
            _append_manifest(manifest_path, manifest_entry)
            return RouteResult(
                status="routed_drive",
                reason="ok",
                manifest_entry=manifest_entry,
                drive_file_id=drive_file_id,
                drive_file_url=drive_file_url,
            )
        except Exception as exc:
            manifest_entry = _manifest_entry(
                meta=meta,
                size=len(content_bytes),
                sha256=sha256_hex,
                status="error",
                reason=f"route_error:{exc}",
                saved_path=None,
            )
            _append_manifest(manifest_path, manifest_entry)
            return RouteResult(
                status="error",
                reason=f"route_error:{exc}",
                manifest_entry=manifest_entry,
            )

    reason = f"unsupported_route_mode:{mode}"
    manifest_entry = _manifest_entry(
        meta=meta,
        size=len(content_bytes),
        sha256=sha256_hex,
        status="error",
        reason=reason,
        saved_path=None,
    )
    _append_manifest(manifest_path, manifest_entry)
    return RouteResult(status="error", reason=reason, manifest_entry=manifest_entry)


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _normalize_lower_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()

    normalized: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        normalized.add(item.strip().lower())
    return {v for v in normalized if v}


def _sha256_hex(content_bytes: bytes) -> str:
    return hashlib.sha256(content_bytes).hexdigest()


def _manifest_path(run_dir: Path) -> Path:
    return run_dir / "attachments" / "manifest.jsonl"


def _attachments_dir(run_dir: Path, kind: str) -> Path:
    target = run_dir / "attachments" / kind
    target.mkdir(parents=True, exist_ok=True)
    return target


def _manifest_entry(
    *,
    meta: AttachmentMeta,
    size: int,
    sha256: str,
    status: str,
    reason: str,
    saved_path: Path | None,
    drive_file_id: str | None = None,
    drive_file_url: str | None = None,
) -> dict[str, Any]:
    return {
        "filename": meta.filename,
        "mime": meta.mime_type,
        "size": size,
        "sha256": sha256,
        "status": status,
        "reason": reason,
        "saved_path": str(saved_path) if saved_path else "",
        "drive_file_id": drive_file_id,
        "drive_file_url": drive_file_url,
    }


def _append_manifest(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry))
        f.write("\n")


def _safe_filename(filename: str, message_id: str, part_id: str | None) -> str:
    fallback = f"{message_id}_{part_id}" if part_id else message_id
    raw = (filename or "").strip() or fallback
    safe_chars = []
    for ch in raw:
        if ch in {"\\", "/", ":", "*", "?", '"', "<", ">", "|"}:
            safe_chars.append("_")
        else:
            safe_chars.append(ch)

    safe = "".join(safe_chars).strip().strip(".")
    safe = "".join(ch for ch in safe if ch.isprintable())

    if not safe:
        return f"{fallback}.bin"
    if len(safe) > 180:
        safe = safe[:180]
    return safe


def _next_available_path(directory: Path, filename: str) -> Path:
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

    raise RuntimeError(f"Unable to allocate unique filename for {filename}")
