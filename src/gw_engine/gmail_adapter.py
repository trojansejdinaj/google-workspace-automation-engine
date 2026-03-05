from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gw_engine.clients import GmailService
from gw_engine.gmail_decode import extract_parts, safe_base64url_decode
from gw_engine.logger import JsonlLogger


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        try:
            return int(normalized)
        except ValueError:
            return None
    return None


def _find_header_value(part: dict[str, Any], name: str) -> str | None:
    headers = part.get("headers")
    if not isinstance(headers, list):
        return None

    name_lower = name.lower()
    for header in headers:
        if not isinstance(header, dict):
            continue

        header_name = str(header.get("name") or "").strip().lower()
        header_value = header.get("value")
        if header_name == name_lower and isinstance(header_value, str):
            return header_value
    return None


def _extract_header_param_value(value: str, param: str) -> str | None:
    for chunk in value.split(";")[1:]:
        chunk = chunk.strip()
        if "=" not in chunk:
            continue

        raw_key, raw_value = chunk.split("=", 1)
        if raw_key.strip().lower() not in {param.lower(), f"{param.lower()}*"}:
            continue

        clean = raw_value.strip().strip("\"'")
        if clean:
            return clean.split("''")[-1]
    return None


def _decode_part_filename(part: dict[str, Any]) -> str:
    filename = part.get("filename")
    if isinstance(filename, str) and filename.strip():
        return filename.strip()

    content_disposition = _find_header_value(part, "Content-Disposition")
    if isinstance(content_disposition, str):
        extracted = _extract_header_param_value(content_disposition, "filename")
        if extracted:
            return extracted.strip()

    content_type = _find_header_value(part, "Content-Type")
    if isinstance(content_type, str):
        extracted = _extract_header_param_value(content_type, "name")
        if extracted:
            return extracted.strip()

    return ""


def _decode_part_mime_type(part: dict[str, Any]) -> str:
    mime_type = part.get("mimeType")
    if isinstance(mime_type, str):
        normalized = mime_type.strip().split(";", 1)[0].strip()
        if normalized:
            return normalized

    content_type = _find_header_value(part, "Content-Type")
    if isinstance(content_type, str):
        normalized = content_type.strip().split(";", 1)[0].strip()
        if normalized:
            return normalized

    return ""


@dataclass(frozen=True)
class AttachmentMeta:
    filename: str
    mime_type: str
    size_estimate: int | None
    attachment_id: str
    part_id: str | None
    message_id: str


class GmailAdapter:
    def __init__(self, service: GmailService, logger: JsonlLogger, run_id: str) -> None:
        self._service = service
        self._logger = logger
        self._run_id = run_id

    def list_labels(self) -> list[dict[str, Any]]:
        """List Gmail labels. Re-running add/remove operations with IDs from this method is idempotent."""
        self._logger.info(
            "gmail_list_labels_start",
            run_id=self._run_id,
        )

        try:
            response = self._service.users().labels().list(userId="me").execute()
        except Exception as exc:
            raise RuntimeError("Gmail list labels failed while fetching labels") from exc

        labels = response.get("labels", []) if isinstance(response, dict) else []
        return [label for label in labels if isinstance(label, dict)]

    def get_label_id_by_name(self, name: str) -> str | None:
        """Return matching label id for label name using case-insensitive comparison."""
        for label in self.list_labels():
            if (
                isinstance(label.get("name"), str)
                and label["name"].lower() == name.lower()
                and isinstance(label.get("id"), str)
            ):
                return label["id"]
        return None

    def ensure_label(self, name: str) -> str:
        """Ensure a Gmail label exists; create if missing.

        Using add/remove label operations on the same message state is idempotent.
        """
        label_id = self.get_label_id_by_name(name)
        if label_id is not None:
            self._logger.info(
                "gmail_label_exists",
                run_id=self._run_id,
                name=name,
                label_id=label_id,
            )
            return label_id

        self._logger.info(
            "gmail_label_create_start",
            run_id=self._run_id,
            name=name,
        )

        try:
            response = (
                self._service.users()
                .labels()
                .create(
                    userId="me",
                    body={
                        "name": name,
                        "labelListVisibility": "labelShow",
                        "messageListVisibility": "show",
                    },
                )
                .execute()
            )
        except Exception as exc:
            raise RuntimeError("Gmail ensure label failed while creating label") from exc

        created_id = response.get("id") if isinstance(response, dict) else None
        if not isinstance(created_id, str):
            raise RuntimeError("Gmail ensure label failed to create label id")

        self._logger.info(
            "gmail_label_created",
            run_id=self._run_id,
            name=name,
            label_id=created_id,
        )
        return created_id

    def modify_message_labels(
        self,
        message_id: str,
        add_label_ids: list[str],
        remove_label_ids: list[str],
    ) -> None:
        """Apply label adds/removes for a message. Operation is idempotent on repeated runs."""
        try:
            self._service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": add_label_ids, "removeLabelIds": remove_label_ids},
            ).execute()
        except Exception as exc:
            raise RuntimeError(
                f"Gmail modify message labels failed for message {message_id}"
            ) from exc

        self._logger.info(
            "gmail_modify_labels_ok",
            run_id=self._run_id,
            message_id=message_id,
            add_label_ids=add_label_ids,
            remove_label_ids=remove_label_ids,
        )

    def batch_modify(
        self,
        message_ids: list[str],
        add_label_ids: list[str],
        remove_label_ids: list[str],
    ) -> None:
        """Apply label adds/removes in batch. Empty input is treated as a no-op."""
        if not message_ids:
            return

        try:
            self._service.users().messages().batchModify(
                userId="me",
                body={
                    "ids": message_ids,
                    "addLabelIds": add_label_ids,
                    "removeLabelIds": remove_label_ids,
                },
            ).execute()
        except Exception as exc:
            raise RuntimeError("Gmail batch modify labels failed for message batch") from exc

        self._logger.info(
            "gmail_batch_modify_ok",
            run_id=self._run_id,
            count=len(message_ids),
            add_label_ids=add_label_ids,
            remove_label_ids=remove_label_ids,
        )

    def search_message_ids(self, query: str, max_results: int = 50) -> list[str]:
        self._logger.info(
            "gmail_search_start",
            run_id=self._run_id,
            query=query,
            max_results=max_results,
        )

        try:
            response = (
                self._service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
        except Exception as exc:
            raise RuntimeError("Gmail search failed while listing message ids") from exc

        messages = response.get("messages", []) if isinstance(response, dict) else []
        message_ids = [
            str(message["id"])
            for message in messages
            if isinstance(message, dict) and "id" in message
        ]

        self._logger.info(
            "gmail_search_ok",
            run_id=self._run_id,
            query=query,
            max_results=max_results,
            count=len(message_ids),
        )

        return message_ids

    def fetch_messages(self, message_ids: list[str], format: str = "full") -> list[dict[str, Any]]:
        if not message_ids:
            return []

        self._logger.info(
            "gmail_fetch_start",
            run_id=self._run_id,
            count=len(message_ids),
        )

        messages: list[dict[str, Any]] = []
        try:
            for message_id in message_ids:
                message = (
                    self._service.users()
                    .messages()
                    .get(userId="me", id=message_id, format=format)
                    .execute()
                )
                if isinstance(message, dict):
                    messages.append(message)
                else:
                    messages.append({"raw": message})
        except Exception as exc:
            raise RuntimeError("Gmail fetch failed while retrieving message details") from exc

        self._logger.info(
            "gmail_fetch_ok",
            run_id=self._run_id,
            count=len(messages),
        )

        return messages

    def list_message_attachments(self, message_id: str) -> list[AttachmentMeta]:
        self._logger.info(
            "gmail_list_attachments_start",
            run_id=self._run_id,
            message_id=message_id,
        )

        try:
            message = (
                self._service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
        except Exception as exc:
            raise RuntimeError(
                f"Gmail list attachments failed while loading message {message_id}"
            ) from exc

        payload = message.get("payload") if isinstance(message, dict) else None
        if not isinstance(payload, dict):
            self._logger.debug(
                "gmail_list_attachments_no_payload",
                run_id=self._run_id,
                message_id=message_id,
            )
            return []

        attachments: list[AttachmentMeta] = []
        for part in extract_parts(payload):
            body = part.get("body")
            if not isinstance(body, dict):
                continue

            attachment_id_raw = body.get("attachmentId")
            if not isinstance(attachment_id_raw, str) or not attachment_id_raw.strip():
                continue

            part_id = part.get("partId")
            part_id_value = str(part_id) if part_id is not None else None

            attachments.append(
                AttachmentMeta(
                    filename=_decode_part_filename(part),
                    mime_type=_decode_part_mime_type(part),
                    size_estimate=_coerce_int(body.get("size")),
                    attachment_id=attachment_id_raw,
                    part_id=part_id_value,
                    message_id=message_id,
                )
            )

        self._logger.info(
            "gmail_list_attachments_ok",
            run_id=self._run_id,
            message_id=message_id,
            count=len(attachments),
        )

        return attachments

    def get_attachment_bytes(self, message_id: str, attachment_id: str) -> bytes:
        self._logger.info(
            "gmail_get_attachment_start",
            run_id=self._run_id,
            message_id=message_id,
            attachment_id=attachment_id,
        )

        try:
            response = (
                self._service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )
        except Exception as exc:
            raise RuntimeError(
                f"Gmail get attachment failed for {message_id}:{attachment_id}"
            ) from exc

        if not isinstance(response, dict):
            raise RuntimeError(
                f"Gmail get attachment returned non-dict payload for {message_id}:{attachment_id}"
            )

        data = response.get("data")
        if not isinstance(data, str):
            raise RuntimeError(
                f"Gmail get attachment missing data for {message_id}:{attachment_id}"
            )

        try:
            return safe_base64url_decode(data)
        except ValueError as exc:
            raise RuntimeError(
                f"Gmail get attachment failed while decoding {message_id}:{attachment_id}"
            ) from exc
