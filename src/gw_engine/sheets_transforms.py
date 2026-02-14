from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from gw_engine.sheets_validation import InvalidRow

CaseMode = Literal["lower", "upper", "title", "none"]
KeepMode = Literal["first", "last"]


def _collapse_spaces(s: str) -> str:
    return " ".join(s.split())


def _apply_case(s: str, mode: CaseMode) -> str:
    if mode == "none":
        return s
    if mode == "lower":
        return s.lower()
    if mode == "upper":
        return s.upper()
    if mode == "title":
        return s.title()
    return s


def normalize_string(
    v: Any,
    *,
    trim: bool = True,
    collapse_spaces: bool = False,
    case: CaseMode = "none",
) -> str:
    s = "" if v is None else str(v)
    if trim:
        s = s.strip()
    if collapse_spaces:
        s = _collapse_spaces(s)
    s = _apply_case(s, case)
    return s


def normalize_number(v: Any, *, strip_commas: bool = True) -> float:
    # Reject bool (True is an int in Python)
    if isinstance(v, bool):
        raise ValueError("bool is not a number")
    if isinstance(v, int | float):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            raise ValueError("blank")
        if strip_commas:
            s = s.replace(",", "")
        return float(s)
    raise ValueError(f"not a number: {type(v).__name__}")


def normalize_date_to_iso(v: Any, *, formats: list[str]) -> str:
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            raise ValueError("blank")
        # Try provided formats in order
        for fmt in formats:
            try:
                dt = datetime.strptime(s, fmt)
                return dt.date().isoformat()
            except ValueError:
                continue
        raise ValueError("unparseable date")
    raise ValueError(f"not a date string: {type(v).__name__}")


def apply_transforms(
    rows: list[dict[str, Any]],
    *,
    schema: dict[str, Any],
    transforms_cfg: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[InvalidRow]]:
    """
    Apply cleanup transforms BEFORE strict schema validation.

    Returns:
      - transformed rows (same shape dicts)
      - InvalidRow entries for transform failures
    """
    strings_cfg: dict[str, Any] = transforms_cfg.get("strings", {})
    dates_cfg: dict[str, Any] = transforms_cfg.get("dates", {})
    numbers_cfg: dict[str, Any] = transforms_cfg.get("numbers", {})

    trim: bool = bool(strings_cfg.get("trim", True))
    collapse_spaces: bool = bool(strings_cfg.get("collapse_spaces", False))
    case_map: dict[str, Any] = strings_cfg.get("case", {}) or {}

    date_formats: list[str] = list(dates_cfg.get("formats", []) or ["%Y-%m-%d"])
    strip_commas: bool = bool(numbers_cfg.get("strip_commas", True))

    out: list[dict[str, Any]] = []
    invalid: list[InvalidRow] = []

    for idx, row in enumerate(rows):
        new_row = dict(row)
        reasons: list[str] = []

        for col_name, spec in (schema or {}).items():
            # schema spec is dict-like from cfg; we only need 'type'
            col_type = (spec or {}).get("type")
            if col_name not in new_row:
                continue  # validation handles missing required columns

            v = new_row.get(col_name)

            try:
                if col_type == "string":
                    mode_raw = case_map.get(col_name, "none")
                    mode: CaseMode = (
                        mode_raw if mode_raw in {"lower", "upper", "title", "none"} else "none"
                    )
                    new_row[col_name] = normalize_string(
                        v,
                        trim=trim,
                        collapse_spaces=collapse_spaces,
                        case=mode,
                    )
                elif col_type == "date_iso":
                    # normalize to strict ISO
                    new_row[col_name] = normalize_date_to_iso(v, formats=date_formats)
                elif col_type == "number":
                    new_row[col_name] = normalize_number(v, strip_commas=strip_commas)
                else:
                    # bool or unknown: leave as-is (validation will handle)
                    pass
            except Exception as e:
                reasons.append(f"{col_name}: {e}")

        if reasons:
            invalid.append(InvalidRow(row_idx=idx, row=row, reasons=reasons))
        out.append(new_row)

    return out, invalid


def dedupe_rows(
    rows: list[dict[str, Any]],
    *,
    keys: list[str],
    keep: KeepMode = "first",
) -> tuple[list[dict[str, Any]], int]:
    """
    Dedupe by config-driven key columns.
    Uses already-normalized values.
    If any key is missing/blank, the row is treated as unique (not deduped).
    """
    seen: dict[tuple[Any, ...], int] = {}
    out: list[dict[str, Any]] = []

    removed = 0
    for row in rows:
        key_vals = []
        missing_or_blank = False
        for k in keys:
            v = row.get(k)
            if v is None or (isinstance(v, str) and v.strip() == ""):
                missing_or_blank = True
                break
            key_vals.append(v)

        if missing_or_blank:
            out.append(row)
            continue

        key = tuple(key_vals)
        if key not in seen:
            seen[key] = len(out)
            out.append(row)
            continue

        # duplicate
        if keep == "first":
            removed += 1
            continue

        # keep == "last": replace existing
        removed += 1
        out[seen[key]] = row

    return out, removed
