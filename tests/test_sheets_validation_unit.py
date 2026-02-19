from __future__ import annotations

from datetime import date

import pytest

from gw_engine.sheets_validation import (
    ColumnSpec,
    build_schema_from_cfg,
    mark_rows_with_reasons,
    validate_rows,
)


@pytest.mark.parametrize(
    ("col_type", "raw_value", "expected"),
    [
        ("string", "  hello  ", "hello"),
        ("number", "1,234.50", 1234.5),
        ("bool", "Yes", True),
        ("date_iso", date(2026, 2, 19), "2026-02-19"),
    ],
)
def test_validate_rows_coerces_supported_types(
    col_type: str,
    raw_value: object,
    expected: object,
) -> None:
    schema = [ColumnSpec(name="v", type=col_type, required=True, allow_blank=False)]

    res = validate_rows(rows=[{"v": raw_value}], schema=schema)

    assert res.rows_in == 1
    assert res.rows_valid == 1
    assert res.rows_invalid == 0
    assert len(res.valid_rows) == 1
    assert res.valid_rows[0]["v"] == expected


@pytest.mark.parametrize(
    ("col_type", "raw_value"),
    [
        ("number", "not-a-number"),
        ("bool", "maybe"),
        ("date_iso", "02/19/2026"),
    ],
)
def test_validate_rows_reports_stable_type_error_reason_keys(
    col_type: str,
    raw_value: object,
) -> None:
    schema = [ColumnSpec(name="v", type=col_type, required=True, allow_blank=False)]

    res = validate_rows(rows=[{"v": raw_value}], schema=schema)

    assert res.rows_in == 1
    assert res.rows_valid == 0
    assert res.rows_invalid == 1
    assert len(res.invalid_rows) == 1

    reasons = res.invalid_rows[0].reasons
    reason = next((r for r in reasons if r.startswith("type_error:")), "")
    assert reason

    code, column, expected_type = reason.split(":")
    assert code == "type_error"
    assert column == "v"
    assert expected_type == col_type


@pytest.mark.parametrize(
    "row",
    [
        {},
        {"id": ""},
        {"id": "   "},
        {"id": None},
    ],
)
def test_required_columns_are_enforced_with_stable_reason_code(row: dict[str, object]) -> None:
    schema = [ColumnSpec(name="id", type="string", required=True, allow_blank=False)]

    res = validate_rows(rows=[row], schema=schema)

    assert res.rows_in == 1
    assert res.rows_valid == 0
    assert res.rows_invalid == 1

    reasons = res.invalid_rows[0].reasons
    assert "missing_required:id" in reasons
    assert reasons.count("missing_required:id") == 1


def test_blank_not_allowed_emits_stable_reason_code() -> None:
    schema = [ColumnSpec(name="note", type="string", required=False, allow_blank=False)]

    res = validate_rows(rows=[{"note": ""}], schema=schema)

    assert res.rows_in == 1
    assert res.rows_valid == 0
    assert res.rows_invalid == 1
    assert "blank_not_allowed:note" in res.invalid_rows[0].reasons


def test_rows_metrics_and_marked_output_consistency() -> None:
    rules = {
        "schema": {
            "id": {"type": "string", "required": True, "allow_blank": False},
            "amount": {"type": "number", "required": True, "allow_blank": False},
        }
    }
    schema = build_schema_from_cfg(rules)
    rows = [
        {"id": "A-1", "amount": "3.50"},
        {"id": "A-2", "amount": "oops"},
        {"amount": "1.00"},
    ]

    res = validate_rows(rows=rows, schema=schema)

    assert res.rows_in == 3
    assert res.rows_valid == len(res.valid_rows)
    assert res.rows_invalid == len(res.invalid_rows)
    assert res.rows_valid == 1
    assert res.rows_invalid == 2

    invalid_count = res.rows_invalid
    rows_out = res.rows_valid
    assert invalid_count == 2
    assert rows_out == 1

    marked = mark_rows_with_reasons(rows, res.invalid_rows)
    assert len(marked) == res.rows_in
    assert marked[0]["_gw_valid"] is True
    assert marked[0]["_gw_reasons"] == ""
    assert marked[1]["_gw_valid"] is False
    assert marked[2]["_gw_valid"] is False
