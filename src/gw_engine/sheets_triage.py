from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

TRIAGE_REQUIRED_COLUMNS = [
    "message_id",
    "thread_id",
    "date",
    "from",
    "subject",
    "name",
    "company",
    "email",
    "phone",
    "amount",
    "invoice_or_order_id",
    "confidence",
    "gmail_link",
    "status",
    "last_run_id",
    "updated_at",
]


def now_utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def build_gmail_permalink(message_id: str, *, mailbox_index: int = 0, anchor: str = "inbox") -> str:
    mid = (message_id or "").strip()
    if not mid:
        return ""
    # Typical permalink format works for most accounts
    return f"https://mail.google.com/mail/u/{mailbox_index}/#{anchor}/{mid}"


def _normalize_table(values: list[list[Any]]) -> list[list[str]]:
    """Coerce to rectangular string table."""
    if not values:
        return []
    width = max(len(r) for r in values)
    out: list[list[str]] = []
    for r in values:
        row = ["" if c is None else str(c) for c in r]
        if len(row) < width:
            row = row + [""] * (width - len(row))
        out.append(row)
    return out


def _ensure_columns(table: list[list[str]], required_cols: list[str]) -> list[list[str]]:
    if not table:
        return [required_cols]

    header = table[0]
    existing = {c: i for i, c in enumerate(header)}
    new_header = header[:]
    for col in required_cols:
        if col not in existing:
            new_header.append(col)

    if new_header == header:
        return table

    # pad rows to new width
    new_width = len(new_header)
    out = [new_header]
    for r in table[1:]:
        rr = r[:]
        if len(rr) < new_width:
            rr += [""] * (new_width - len(rr))
        out.append(rr)
    return out


def upsert_triage_table(
    existing_values: list[list[Any]],
    new_rows: list[dict[str, Any]],
    *,
    default_status: str = "NEW",
    preserve_existing_status: bool = True,
    run_id: str = "",
    mailbox_index: int = 0,
    anchor: str = "inbox",
    updated_at: str | None = None,
) -> list[list[str]]:
    """
    Upsert rows keyed by message_id into a tabular values matrix.
    Returns full table (including header).
    """
    updated_at = updated_at or now_utc_iso()

    table = _normalize_table(existing_values)
    if not table:
        table = [TRIAGE_REQUIRED_COLUMNS]

    table = _ensure_columns(table, TRIAGE_REQUIRED_COLUMNS)

    header = table[0]
    col_idx = {c: i for i, c in enumerate(header)}
    key_i = col_idx["message_id"]
    status_i = col_idx["status"]

    # Build index of existing keys -> row position
    index: dict[str, int] = {}
    for rpos in range(1, len(table)):
        key = (table[rpos][key_i] or "").strip()
        if key and key not in index:
            index[key] = rpos

    def to_cell_map(row: dict[str, Any]) -> dict[str, str]:
        # parsed fields live under row["parsed"] sometimes
        parsed = row.get("parsed") if isinstance(row.get("parsed"), dict) else {}
        message_id = str(row.get("message_id") or "").strip()

        # normalize amount
        amount_val = parsed.get("amount")
        amount = "" if amount_val is None else str(amount_val)

        out = {
            "message_id": message_id,
            "thread_id": str(row.get("thread_id") or ""),
            "date": str(row.get("date") or ""),
            "from": str(row.get("from") or ""),
            "subject": str(row.get("subject") or ""),
            "name": str(parsed.get("name") or ""),
            "company": str(parsed.get("company") or ""),
            "email": str(parsed.get("email") or ""),
            "phone": str(parsed.get("phone") or ""),
            "amount": amount,
            "invoice_or_order_id": str(parsed.get("invoice_or_order_id") or ""),
            "confidence": str(row.get("parser_confidence") or row.get("parse_confidence") or ""),
            "gmail_link": build_gmail_permalink(
                message_id, mailbox_index=mailbox_index, anchor=anchor
            ),
            "last_run_id": run_id,
            "updated_at": updated_at,
        }
        return out

    # Apply upserts
    for row in new_rows:
        cells = to_cell_map(row)
        mid = cells["message_id"]
        if not mid:
            continue

        if mid in index:
            rpos = index[mid]
            existing_status = table[rpos][status_i] if status_i < len(table[rpos]) else ""
            for col, val in cells.items():
                table[rpos][col_idx[col]] = val
            if preserve_existing_status and existing_status.strip():
                table[rpos][status_i] = existing_status
            else:
                table[rpos][status_i] = default_status
        else:
            new_r = [""] * len(header)
            for col, val in cells.items():
                new_r[col_idx[col]] = val
            new_r[status_i] = default_status
            table.append(new_r)
            index[mid] = len(table) - 1

    return table
