from __future__ import annotations

from typing import TypedDict


class ActionItem(TypedDict):
    """Data contract for Gmail action planning.

    Pure planning functions only; no Gmail API calls here.
    This separation supports idempotent reruns and deterministic unit tests.
    """

    message_id: str
    parse_ok: bool
    error_count: int
    confidence: float


def classify_action(item: ActionItem, *, min_confidence: float) -> str:
    """Classify message action based on parse outcome and confidence."""
    return (
        "success" if item["parse_ok"] and item["confidence"] >= min_confidence else "needs_review"
    )


def build_action_plan(
    items: list[ActionItem],
    *,
    min_confidence: float,
) -> dict[str, list[str]]:
    """Build action buckets from items.

    Dedupe message IDs while preserving input order (first occurrence wins).
    """
    plan: dict[str, list[str]] = {"success": [], "needs_review": []}
    seen: set[str] = set()

    for item in items:
        message_id = item["message_id"]
        if message_id in seen:
            continue

        seen.add(message_id)
        action = classify_action(item, min_confidence=min_confidence)
        if action == "success":
            plan["success"].append(message_id)
        else:
            plan["needs_review"].append(message_id)

    return plan


def summarize_plan(plan: dict[str, list[str]]) -> dict[str, int]:
    """Return counts for a built action plan."""
    return {
        "success_count": len(plan.get("success", [])),
        "needs_review_count": len(plan.get("needs_review", [])),
    }
