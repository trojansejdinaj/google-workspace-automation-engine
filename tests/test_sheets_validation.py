from gw_engine.sheets_validation import build_schema_from_cfg, mark_rows_with_reasons, validate_rows


def test_validation_marks_invalid_rows_with_reasons() -> None:
    rules = {
        "schema": {
            "id": {"type": "string", "required": True, "allow_blank": False},
            "date": {"type": "date_iso", "required": True, "allow_blank": False},
            "amount": {"type": "number", "required": True, "allow_blank": False},
        }
    }
    schema = build_schema_from_cfg(rules)

    rows = [
        {"id": "A-1", "date": "2026-02-01", "amount": "3.5"},
        {"id": "", "date": "2026-02-01", "amount": "3.5"},  # blank id
        {"id": "A-3", "date": "02/01/2026", "amount": "3.5"},  # bad date format
        {"id": "A-4", "date": "2026-02-01", "amount": "abc"},  # bad number
        {"date": "2026-02-01", "amount": "1.0"},  # missing id key
    ]

    res = validate_rows(rows, schema)
    assert res.rows_in == 5
    assert res.rows_valid == 1
    assert res.rows_invalid == 4

    # ensure we never silently drop: invalid rows are explicitly returned with reasons
    reasons = {x.row_idx: x.reasons for x in res.invalid_rows}
    assert 1 in reasons and any(
        r.startswith("missing_required:id") or r.startswith("blank_not_allowed:id")
        for r in reasons[1]
    )
    assert 2 in reasons and any(r.startswith("type_error:date:date_iso") for r in reasons[2])
    assert 3 in reasons and any(r.startswith("type_error:amount:number") for r in reasons[3])
    assert 4 in reasons and any(r.startswith("missing_required:id") for r in reasons[4])

    marked = mark_rows_with_reasons(rows, res.invalid_rows)
    assert marked[0]["_gw_valid"] is True
    assert marked[1]["_gw_valid"] is False
    assert marked[1]["_gw_reasons"] != ""
