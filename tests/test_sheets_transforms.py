from gw_engine.sheets_transforms import apply_transforms, dedupe_rows


def test_apply_transforms_normalizes_string_date_number() -> None:
    schema = {
        "id": {"type": "string"},
        "date": {"type": "date_iso"},
        "amount": {"type": "number"},
        "category": {"type": "string"},
    }

    cfg = {
        "strings": {"trim": True, "collapse_spaces": True, "case": {"category": "lower"}},
        "dates": {"formats": ["%Y-%m-%d", "%d/%m/%Y"]},
        "numbers": {"strip_commas": True},
    }

    rows = [
        {"id": " A-1 ", "date": "02/03/2026", "amount": "1,200.50", "category": " FOOD  "},
    ]

    out, invalid = apply_transforms(rows, schema=schema, transforms_cfg=cfg)
    assert invalid == []
    assert out[0]["id"] == "A-1"
    assert out[0]["date"] == "2026-03-02"
    assert out[0]["amount"] == 1200.5
    assert out[0]["category"] == "food"


def test_apply_transforms_marks_invalid_on_bad_date_or_number() -> None:
    schema = {"date": {"type": "date_iso"}, "amount": {"type": "number"}}
    cfg = {"dates": {"formats": ["%Y-%m-%d"]}, "numbers": {"strip_commas": True}}

    rows = [{"date": "02/03/2026", "amount": "abc"}]
    _, invalid = apply_transforms(rows, schema=schema, transforms_cfg=cfg)
    assert len(invalid) == 1
    assert "date:" in invalid[0].reasons[0] or "amount:" in invalid[0].reasons[0]


def test_dedupe_rows_keep_first() -> None:
    rows = [{"id": "A-1", "v": 1}, {"id": "A-1", "v": 2}, {"id": "A-2", "v": 3}]
    out, removed = dedupe_rows(rows, keys=["id"], keep="first")
    assert removed == 1
    assert out == [{"id": "A-1", "v": 1}, {"id": "A-2", "v": 3}]


def test_dedupe_rows_keep_last() -> None:
    rows = [{"id": "A-1", "v": 1}, {"id": "A-1", "v": 2}]
    out, removed = dedupe_rows(rows, keys=["id"], keep="last")
    assert removed == 1
    assert out == [{"id": "A-1", "v": 2}]
