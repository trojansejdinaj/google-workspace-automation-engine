from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

SchemaType = Literal["string", "number", "bool", "date_iso"]


class SchemaError(ValueError):
    pass


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    type: SchemaType
    required: bool = False
    allow_blank: bool = True


@dataclass(frozen=True)
class InvalidRow:
    row_idx: int  # 0-based
    row: dict[str, Any]
    reasons: list[str]


@dataclass(frozen=True)
class ValidationResult:
    valid_rows: list[dict[str, Any]]
    invalid_rows: list[InvalidRow]
    # convenience counts
    rows_in: int
    rows_valid: int
    rows_invalid: int


def _is_blank(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    return False


def _to_string(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _to_number(v: Any) -> float:
    if isinstance(v, int | float) and not isinstance(v, bool):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            raise ValueError("blank")
        # tolerate commas in human sheets: "1,234.50"
        s = s.replace(",", "")
        return float(s)
    raise ValueError(f"not a number: {type(v).__name__}")


def _to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, int | float) and not isinstance(v, bool):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"true", "t", "yes", "y", "1"}:
            return True
        if s in {"false", "f", "no", "n", "0"}:
            return False
    raise ValueError("not a bool")


def _to_date_iso(v: Any) -> str:
    # Keep output as ISO string ("YYYY-MM-DD") to match Sheets-friendly values.
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            raise ValueError("blank")
        # strict ISO only for now (T2)
        parts = s.split("-")
        if len(parts) != 3:
            raise ValueError("not iso date")
        yyyy, mm, dd = parts
        if len(yyyy) != 4 or len(mm) != 2 or len(dd) != 2:
            raise ValueError("not iso date")
        # basic numeric validation
        y = int(yyyy)
        m = int(mm)
        d = int(dd)
        _ = date(y, m, d)  # validates actual calendar date
        return s
    raise ValueError("not iso date")


def coerce_value(value: Any, t: SchemaType) -> Any:
    if t == "string":
        return _to_string(value)
    if t == "number":
        return _to_number(value)
    if t == "bool":
        return _to_bool(value)
    if t == "date_iso":
        return _to_date_iso(value)
    raise SchemaError(f"Unknown schema type: {t}")


def build_schema_from_cfg(rules: dict[str, Any]) -> list[ColumnSpec]:
    schema_cfg = rules.get("schema")
    required = rules.get("required_columns") or []
    optional = rules.get("optional_columns") or []

    if schema_cfg is None:
        # fallback: everything is string
        cols: list[ColumnSpec] = []
        for c in required:
            cols.append(ColumnSpec(name=str(c), type="string", required=True, allow_blank=False))
        for c in optional:
            cols.append(ColumnSpec(name=str(c), type="string", required=False, allow_blank=True))
        return cols

    if not isinstance(schema_cfg, dict):
        raise SchemaError("rules.schema must be a mapping of column -> spec")

    cols = []
    for col_name, spec in schema_cfg.items():
        if not isinstance(spec, dict):
            raise SchemaError(f"rules.schema.{col_name} must be a mapping")
        t = spec.get("type")
        if t not in {"string", "number", "bool", "date_iso"}:
            raise SchemaError(
                f"rules.schema.{col_name}.type must be one of: string, number, bool, date_iso"
            )
        required_flag = bool(spec.get("required", False))
        allow_blank = bool(spec.get("allow_blank", True))
        cols.append(
            ColumnSpec(name=str(col_name), type=t, required=required_flag, allow_blank=allow_blank)
        )

    return cols


def validate_rows(rows: list[dict[str, Any]], schema: list[ColumnSpec]) -> ValidationResult:
    by_name = {c.name: c for c in schema}
    valid: list[dict[str, Any]] = []
    invalid: list[InvalidRow] = []

    for idx, row in enumerate(rows):
        reasons: list[str] = []
        out: dict[str, Any] = dict(row)

        # validate/coerce schema columns
        for col in schema:
            raw = row.get(col.name)

            if col.required and _is_blank(raw):
                reasons.append(f"missing_required:{col.name}")
                continue

            if _is_blank(raw):
                # blank ok only if allow_blank
                if not col.allow_blank:
                    reasons.append(f"blank_not_allowed:{col.name}")
                # normalize blanks to empty string for string type, else keep None
                if col.type == "string":
                    out[col.name] = ""
                else:
                    out[col.name] = None
                continue

            try:
                out[col.name] = coerce_value(raw, col.type)
            except Exception:
                reasons.append(f"type_error:{col.name}:{col.type}")

        # also enforce: if a required column is absent entirely
        for col_name, col in by_name.items():
            if col.required and col_name not in row:
                # avoid double-report if already flagged missing_required via blank logic
                if f"missing_required:{col_name}" not in reasons:
                    reasons.append(f"missing_required:{col_name}")

        if reasons:
            invalid.append(InvalidRow(row_idx=idx, row=row, reasons=reasons))
        else:
            valid.append(out)

    return ValidationResult(
        valid_rows=valid,
        invalid_rows=invalid,
        rows_in=len(rows),
        rows_valid=len(valid),
        rows_invalid=len(invalid),
    )


def mark_rows_with_reasons(
    rows: list[dict[str, Any]], invalid_rows: list[InvalidRow]
) -> list[dict[str, Any]]:
    """
    Marks rows instead of dropping them:
      _gw_valid: true/false
      _gw_reasons: pipe-separated reasons (only for invalid)
    """
    invalid_by_idx = {x.row_idx: x for x in invalid_rows}
    marked: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        out = dict(row)
        inv = invalid_by_idx.get(idx)
        if inv is None:
            out["_gw_valid"] = True
            out["_gw_reasons"] = ""
        else:
            out["_gw_valid"] = False
            out["_gw_reasons"] = "|".join(inv.reasons)
        marked.append(out)

    return marked
