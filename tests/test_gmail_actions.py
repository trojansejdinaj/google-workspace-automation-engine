from __future__ import annotations

from gw_engine.gmail_actions import ActionItem, build_action_plan, classify_action


def test_classify_action_success_when_parse_ok_and_confident_enough() -> None:
    item: ActionItem = ActionItem(
        message_id="m1",
        parse_ok=True,
        error_count=0,
        confidence=0.92,
    )
    assert classify_action(item, min_confidence=0.9) == "success"


def test_classify_action_needs_review_when_confidence_too_low() -> None:
    item: ActionItem = ActionItem(
        message_id="m2",
        parse_ok=True,
        error_count=0,
        confidence=0.75,
    )
    assert classify_action(item, min_confidence=0.8) == "needs_review"


def test_classify_action_needs_review_when_parse_failed() -> None:
    item: ActionItem = ActionItem(
        message_id="m3",
        parse_ok=False,
        error_count=2,
        confidence=0.99,
    )
    assert classify_action(item, min_confidence=0.1) == "needs_review"


def test_build_action_plan_dedupes_and_preserves_first_order() -> None:
    items: list[ActionItem] = [
        ActionItem(
            message_id="m1",
            parse_ok=True,
            error_count=0,
            confidence=0.9,
        ),
        ActionItem(
            message_id="m2",
            parse_ok=False,
            error_count=1,
            confidence=0.5,
        ),
        ActionItem(
            message_id="m1",
            parse_ok=False,
            error_count=0,
            confidence=0.99,
        ),
        ActionItem(
            message_id="m3",
            parse_ok=True,
            error_count=0,
            confidence=0.4,
        ),
        ActionItem(
            message_id="m2",
            parse_ok=True,
            error_count=0,
            confidence=0.95,
        ),
    ]
    plan = build_action_plan(items, min_confidence=0.7)

    assert plan["success"] == ["m1"]
    assert plan["needs_review"] == ["m2", "m3"]


def test_build_action_plan_empty_returns_empty_lists() -> None:
    assert build_action_plan([], min_confidence=0.6) == {
        "success": [],
        "needs_review": [],
    }
