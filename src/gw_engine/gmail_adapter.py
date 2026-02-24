from __future__ import annotations

from typing import Any

from gw_engine.clients import GmailService
from gw_engine.logger import JsonlLogger


class GmailAdapter:
    def __init__(self, service: GmailService, logger: JsonlLogger, run_id: str) -> None:
        self._service = service
        self._logger = logger
        self._run_id = run_id

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
