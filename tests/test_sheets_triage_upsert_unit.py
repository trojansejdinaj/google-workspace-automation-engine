from gw_engine.sheets_triage import upsert_triage_table


def test_upsert_inserts_then_updates_preserving_status():
    existing = [
        ["message_id", "status", "subject"],
        ["m1", "IN_PROGRESS", "old subject"],
    ]
    new_rows = [
        {
            "message_id": "m1",
            "subject": "new subject",
            "from": "a",
            "date": "d",
            "thread_id": "t",
            "parsed": {},
        },
        {
            "message_id": "m2",
            "subject": "second",
            "from": "b",
            "date": "d2",
            "thread_id": "t2",
            "parsed": {},
        },
    ]

    merged = upsert_triage_table(existing, new_rows, default_status="NEW", run_id="RUN123")

    # header present
    assert merged[0][0] == "message_id"

    # m1 preserved status
    m1 = [r for r in merged[1:] if r[0] == "m1"][0]
    status_idx = merged[0].index("status")
    subject_idx = merged[0].index("subject")
    assert m1[status_idx] == "IN_PROGRESS"
    assert m1[subject_idx] == "new subject"

    # m2 inserted with default status
    m2 = [r for r in merged[1:] if r[0] == "m2"][0]
    assert m2[status_idx] == "NEW"
