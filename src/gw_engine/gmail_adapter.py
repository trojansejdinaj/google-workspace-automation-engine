from __future__ import annotations

from typing import Any

from gw_engine.clients import GmailService
from gw_engine.logger import JsonlLogger


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
