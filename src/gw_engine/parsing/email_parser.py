from __future__ import annotations

import re
import unicodedata

from gw_engine.parsing.contracts import ParsedEmail, ParseError

_EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")

_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d().\-\s]{7,}\d)(?!\w)")

_LABEL_CAPTURE_TEMPLATE = r"(?im)^\s*(?:{labels})\s*[:\-]\s*(?P<value>[^\n]+?)\s*$"

_MONEY_RE = re.compile(
    r"\b(?:(?P<code1>USD|EUR|GBP|INR|AUD|CAD)\s*)?"
    r"(?P<symbol>[$€£])?\s*"
    r"(?P<amount>\d{1,3}(?:[ ,]\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"\s*(?P<code2>USD|EUR|GBP|INR|AUD|CAD)?\b",
    re.IGNORECASE,
)

_INVOICE_RE = re.compile(
    r"\binvoice(?:\s*(?:id|number|no\.?|#))?\s*[:#-]?\s*([A-Z0-9][A-Z0-9_/-]{1,})",
    re.IGNORECASE,
)

_ORDER_RE = re.compile(
    r"\border(?:\s*(?:id|number|no\.?|#))?\s*[:#-]?\s*([A-Z0-9][A-Z0-9_/-]{1,})",
    re.IGNORECASE,
)

_CURRENCY_BY_SYMBOL = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
}

_EXPECTED_FIELDS = (
    "name",
    "company",
    "email",
    "phone",
    "amount",
    "invoice_or_order_id",
)

_CANONICAL_TO_LEGACY = {
    "customer_name": "name",
    "company_name": "company",
    "customer_email": "email",
    "customer_phone": "phone",
    "reference_id": "invoice_or_order_id",
}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\u200b", "").replace("\ufeff", "")

    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.split("\n")]
    compact = "\n".join(lines)
    compact = re.sub(r"\n{3,}", "\n\n", compact)
    return compact.strip()


def _label_pattern(labels: list[str]) -> re.Pattern[str]:
    escaped = "|".join(re.escape(label) for label in labels)
    return re.compile(_LABEL_CAPTURE_TEMPLATE.format(labels=escaped))


def _extract_label_values(text: str, labels: list[str]) -> list[str]:
    pattern = _label_pattern(labels)
    values = [match.group("value").strip() for match in pattern.finditer(text)]
    return [value for value in values if value]


def extract_label_value(text: str, labels: list[str]) -> str | None:
    values = _extract_label_values(text, labels)
    if not values:
        return None
    return values[0]


def extract_first_email(text: str) -> str | None:
    match = _EMAIL_RE.search(text)
    if not match:
        return None
    return match.group(1).lower()


def extract_phone(text: str) -> str | None:
    match = _PHONE_RE.search(text)
    if not match:
        return None

    raw = match.group(0).strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 10 or len(digits) > 15:
        return None

    if raw.startswith("+"):
        return f"+{digits}"
    return digits


def extract_money_amount(text: str) -> dict[str, float | str | None] | None:
    match = _MONEY_RE.search(text)
    if not match:
        return None

    amount_raw = str(match.group("amount") or "").replace(" ", "").replace(",", "")
    if amount_raw == "":
        return None

    try:
        amount = float(amount_raw)
    except ValueError:
        return None

    symbol = match.group("symbol")
    code1 = match.group("code1")
    code2 = match.group("code2")

    currency: str | None = None
    if symbol:
        currency = _CURRENCY_BY_SYMBOL.get(symbol)
    if code1:
        currency = code1.upper()
    if code2:
        currency = code2.upper()

    return {
        "amount": amount,
        "currency": currency,
        "raw": match.group(0).strip(),
    }


def extract_invoice_or_order_id(text: str) -> str | None:
    invoice_match = _INVOICE_RE.search(text)
    if invoice_match:
        return invoice_match.group(1)

    order_match = _ORDER_RE.search(text)
    if order_match:
        return order_match.group(1)

    return None


def _display_name_from_from_addr(from_addr: str | None) -> str | None:
    if not from_addr:
        return None

    candidate = from_addr
    bracket_index = candidate.find("<")
    if bracket_index >= 0:
        candidate = candidate[:bracket_index]

    candidate = candidate.strip().strip('"').strip("'")
    candidate = re.sub(r"\s+", " ", candidate)

    if not candidate:
        return None
    if _EMAIL_RE.fullmatch(candidate):
        return None

    return candidate


def _record_ambiguity(errors: list[ParseError], field: str, values: list[str]) -> None:
    distinct = list(dict.fromkeys(values))
    if len(distinct) > 1:
        errors.append(
            ParseError(
                code="ambiguous_match",
                field=field,
                message=f"Multiple labeled values found for {field}",
            )
        )


def _set_canonical_with_alias(
    fields: dict[str, object],
    *,
    canonical_key: str,
    value: object | None,
) -> None:
    if value is None:
        return

    fields[canonical_key] = value
    legacy_key = _CANONICAL_TO_LEGACY.get(canonical_key)
    if legacy_key:
        fields[legacy_key] = value


def _split_amount_fields(
    amount_data: object | None,
) -> tuple[float | None, str | None, str | None, object | None]:
    if amount_data is None:
        return None, None, None, None

    if isinstance(amount_data, dict):
        amount_raw_value = amount_data.get("raw")
        currency_raw_value = amount_data.get("currency")
        amount_numeric = amount_data.get("amount")

        amount_value: float | None = None
        if isinstance(amount_numeric, int | float) and not isinstance(amount_numeric, bool):
            amount_value = float(amount_numeric)
        elif isinstance(amount_numeric, str):
            try:
                amount_value = float(amount_numeric.strip().replace(",", ""))
            except ValueError:
                amount_value = None

        amount_currency = str(currency_raw_value) if currency_raw_value not in (None, "") else None
        amount_raw = str(amount_raw_value) if amount_raw_value not in (None, "") else None

        legacy_amount = {
            "amount": amount_value,
            "currency": amount_currency,
            "raw": amount_raw,
        }
        return amount_value, amount_currency, amount_raw, legacy_amount

    if isinstance(amount_data, str):
        stripped = amount_data.strip()
        if not stripped:
            return None, None, None, None
        return None, None, stripped, stripped

    return None, None, None, None


def parse_email(subject: str | None, from_addr: str | None, body: str) -> ParsedEmail:
    normalized_subject = normalize_text(subject or "")
    normalized_body = normalize_text(body)
    normalized_from = normalize_text(from_addr or "")

    combined = "\n".join(part for part in [normalized_subject, normalized_body] if part)

    errors: list[ParseError] = []
    fields: dict[str, object] = {}

    name_values = _extract_label_values(normalized_body, ["Name", "Customer Name", "Contact Name"])
    _record_ambiguity(errors, "name", name_values)
    name = name_values[0] if name_values else _display_name_from_from_addr(normalized_from)
    _set_canonical_with_alias(fields, canonical_key="customer_name", value=name)

    company_values = _extract_label_values(normalized_body, ["Company", "Organization", "Org"])
    _record_ambiguity(errors, "company", company_values)
    company = company_values[0] if company_values else None
    _set_canonical_with_alias(fields, canonical_key="company_name", value=company)

    email_values = _extract_label_values(
        normalized_body, ["Email", "Email Address", "Contact Email"]
    )
    _record_ambiguity(errors, "email", email_values)

    email_value = email_values[0] if email_values else None
    if email_value and extract_first_email(email_value) is None:
        errors.append(
            ParseError(
                code="invalid_format",
                field="email",
                message="Labeled email is not a valid email format",
            )
        )
        email_value = None

    if email_value is None:
        email_value = extract_first_email(combined) or extract_first_email(normalized_from)

    _set_canonical_with_alias(fields, canonical_key="customer_email", value=email_value)

    phone_values = _extract_label_values(
        normalized_body, ["Phone", "Phone Number", "Mobile", "Tel", "Telephone"]
    )
    _record_ambiguity(errors, "phone", phone_values)

    phone_value = phone_values[0] if phone_values else None
    if phone_value:
        normalized_phone = extract_phone(phone_value)
        if normalized_phone is None:
            errors.append(
                ParseError(
                    code="invalid_format",
                    field="phone",
                    message="Labeled phone value is not a valid phone format",
                )
            )
            phone_value = None
        else:
            phone_value = normalized_phone

    if phone_value is None:
        phone_value = extract_phone(combined)

    _set_canonical_with_alias(fields, canonical_key="customer_phone", value=phone_value)

    amount_values = _extract_label_values(
        normalized_body,
        ["Amount", "Total", "Total Amount", "Invoice Amount", "Payment Amount"],
    )
    _record_ambiguity(errors, "amount", amount_values)

    amount_value = None
    if amount_values:
        amount_value = extract_money_amount(amount_values[0])
        if amount_value is None:
            errors.append(
                ParseError(
                    code="invalid_format",
                    field="amount",
                    message="Labeled amount value is not a valid money format",
                )
            )

    if amount_value is None:
        amount_value = extract_money_amount(combined)

    amount_numeric_value, amount_currency_value, amount_raw_value, amount_legacy = (
        _split_amount_fields(amount_value)
    )
    if amount_numeric_value is not None:
        fields["amount_value"] = amount_numeric_value
    if amount_currency_value is not None:
        fields["amount_currency"] = amount_currency_value
    if amount_raw_value is not None:
        fields["amount_raw"] = amount_raw_value
    if amount_legacy is not None:
        fields["amount"] = amount_legacy

    id_values = _extract_label_values(
        normalized_body,
        ["Invoice", "Invoice ID", "Invoice #", "Order", "Order ID", "Order #"],
    )
    _record_ambiguity(errors, "invoice_or_order_id", id_values)

    invoice_or_order_id = id_values[0] if id_values else None
    if invoice_or_order_id is None:
        invoice_or_order_id = extract_invoice_or_order_id(combined)

    _set_canonical_with_alias(fields, canonical_key="reference_id", value=invoice_or_order_id)

    for field_name in _EXPECTED_FIELDS:
        if field_name not in fields:
            errors.append(
                ParseError(
                    code="missing_field",
                    field=field_name,
                    message=f"Missing expected field: {field_name}",
                )
            )

    found_count = sum(1 for field_name in _EXPECTED_FIELDS if field_name in fields)
    total_fields = len(_EXPECTED_FIELDS)
    missing_count = total_fields - found_count
    ambiguous_count = sum(1 for error in errors if error.code == "ambiguous_match")
    invalid_count = sum(1 for error in errors if error.code == "invalid_format")

    confidence = (
        (found_count / total_fields)
        - (0.08 * missing_count)
        - (0.12 * ambiguous_count)
        - (0.08 * invalid_count)
    )
    confidence = max(0.0, min(1.0, round(confidence, 3)))

    return ParsedEmail(fields=fields, confidence=confidence, errors=errors)
