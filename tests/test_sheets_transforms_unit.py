from __future__ import annotations

import pytest

from gw_engine.sheets_transforms import (
    apply_transforms,
    dedupe_rows,
    normalize_date_to_iso,
    normalize_number,
    normalize_string,
)


@pytest.mark.parametrize(
    ("raw", "trim", "collapse_spaces", "case", "expected"),
    [
        ("  Hello World  ", True, False, "none", "Hello World"),
        ("  Mixed   SPACES  ", True, True, "lower", "mixed spaces"),
        ("name", True, False, "upper", "NAME"),
        ("john doe", True, False, "title", "John Doe"),
    ],
)
def test_normalize_string_trim_case_and_space_collapse(
    raw: object,
    trim: bool,
    collapse_spaces: bool,
    case: str,
    expected: str,
) -> None:
    out = normalize_string(raw, trim=trim, collapse_spaces=collapse_spaces, case=case)
    assert out == expected


@pytest.mark.parametrize(
    ("raw", "formats", "expected"),
    [
        ("2026-02-19", ["%Y-%m-%d"], "2026-02-19"),
        (" 19/02/2026 ", ["%d/%m/%Y"], "2026-02-19"),
        ("02-19-2026", ["%m-%d-%Y"], "2026-02-19"),
    ],
)
def test_normalize_date_to_iso_parses_supported_formats(
    raw: object,
    formats: list[str],
    expected: str,
) -> None:
    assert normalize_date_to_iso(raw, formats=formats) == expected


@pytest.mark.parametrize(
    ("raw", "formats", "error_fragment"),
    [
        ("", ["%Y-%m-%d"], "blank"),
        ("2026/02/19", ["%Y-%m-%d"], "unparseable date"),
        ("2026-02-30", ["%Y-%m-%d"], "unparseable date"),
        (None, ["%Y-%m-%d"], "not a date string"),
    ],
)
def test_normalize_date_to_iso_edge_cases(
    raw: object,
    formats: list[str],
    error_fragment: str,
) -> None:
    with pytest.raises(ValueError, match=error_fragment):
        normalize_date_to_iso(raw, formats=formats)


@pytest.mark.parametrize(
    ("raw", "strip_commas", "expected"),
    [
        (" 1,234.50 ", True, 1234.5),
        ("\t2,000\n", True, 2000.0),
        ("1000", True, 1000.0),
        (123, True, 123.0),
    ],
)
def test_normalize_number_cleanup_happy_path(
    raw: object,
    strip_commas: bool,
    expected: float,
) -> None:
    assert normalize_number(raw, strip_commas=strip_commas) == expected


@pytest.mark.parametrize(
    ("raw", "strip_commas", "error_fragment"),
    [
        ("$1,234.50", True, "could not convert string to float"),
        ("€99", True, "could not convert string to float"),
        ("", True, "blank"),
        (True, True, "bool is not a number"),
    ],
)
def test_normalize_number_currency_and_invalid_inputs(
    raw: object,
    strip_commas: bool,
    error_fragment: str,
) -> None:
    with pytest.raises(ValueError, match=error_fragment):
        normalize_number(raw, strip_commas=strip_commas)


def test_apply_transforms_table_driven_with_derived_metrics() -> None:
    schema = {
        "name": {"type": "string"},
        "date": {"type": "date_iso"},
        "amount": {"type": "number"},
    }
    cfg = {
        "strings": {
            "trim": True,
            "collapse_spaces": True,
            "case": {"name": "title"},
        },
        "dates": {"formats": ["%Y-%m-%d", "%d/%m/%Y"]},
        "numbers": {"strip_commas": True},
    }

    rows = [
        {"name": "  jane   doe ", "date": "19/02/2026", "amount": "1,200.00"},
        {"name": "john", "date": "2026-02-30", "amount": "22"},
        {"name": "sue", "date": "2026-02-19", "amount": "$10"},
    ]

    out, invalid = apply_transforms(rows, schema=schema, transforms_cfg=cfg)

    rows_in = len(rows)
    rows_out = len(out)
    invalid_count = len(invalid)

    assert rows_in == 3
    assert rows_out == 3
    assert invalid_count == 2

    assert out[0]["name"] == "Jane Doe"
    assert out[0]["date"] == "2026-02-19"
    assert out[0]["amount"] == 1200.0

    invalid_by_idx = {item.row_idx: item.reasons for item in invalid}
    assert 1 in invalid_by_idx
    assert any(reason.startswith("date:") for reason in invalid_by_idx[1])
    assert 2 in invalid_by_idx
    assert any(reason.startswith("amount:") for reason in invalid_by_idx[2])


@pytest.mark.parametrize(
    ("keep", "expected_rows", "expected_removed"),
    [
        (
            "first",
            [
                {"id": "A-1", "updated_at": "2026-02-18T10:00:00", "amount": 10},
                {"id": "A-2", "updated_at": "2026-02-18T11:00:00", "amount": 30},
            ],
            1,
        ),
        (
            "last",
            [
                {"id": "A-1", "updated_at": "2026-02-19T10:00:00", "amount": 20},
                {"id": "A-2", "updated_at": "2026-02-18T11:00:00", "amount": 30},
            ],
            1,
        ),
    ],
)
def test_dedupe_rows_strategy_keep_first_or_last(
    keep: str,
    expected_rows: list[dict[str, object]],
    expected_removed: int,
) -> None:
    rows = [
        {"id": "A-1", "updated_at": "2026-02-18T10:00:00", "amount": 10},
        {"id": "A-1", "updated_at": "2026-02-19T10:00:00", "amount": 20},
        {"id": "A-2", "updated_at": "2026-02-18T11:00:00", "amount": 30},
    ]

    out, removed = dedupe_rows(rows, keys=["id"], keep=keep)

    assert out == expected_rows
    assert removed == expected_removed


def test_dedupe_rows_missing_or_blank_key_is_treated_as_unique() -> None:
    rows = [
        {"id": "", "amount": 10},
        {"id": "", "amount": 20},
        {"amount": 30},
        {"id": None, "amount": 40},
    ]

    out, removed = dedupe_rows(rows, keys=["id"], keep="first")

    rows_in = len(rows)
    rows_out = len(out)

    assert removed == 0
    assert rows_in == 4
    assert rows_out == 4
    assert out == rows
