from __future__ import annotations

from pathlib import Path

import pytest

from gw_engine.parsing.email_parser import parse_email

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "emails" / "p03_t3"


def load_fixture(filename: str) -> str:
    return (_FIXTURE_DIR / filename).read_text(encoding="utf-8")


def _assert_alias_consistency(fields: dict[str, object]) -> None:
    alias_pairs = [
        ("customer_name", "name"),
        ("company_name", "company"),
        ("customer_email", "email"),
        ("customer_phone", "phone"),
        ("reference_id", "invoice_or_order_id"),
    ]

    for canonical_key, legacy_key in alias_pairs:
        if canonical_key in fields and legacy_key in fields:
            assert fields[canonical_key] == fields[legacy_key]

    if "amount" in fields and isinstance(fields["amount"], dict):
        amount_data = fields["amount"]
        if "amount_value" in fields:
            assert amount_data.get("amount") == fields["amount_value"]
        if "amount_currency" in fields:
            assert amount_data.get("currency") == fields["amount_currency"]
        if "amount_raw" in fields:
            assert amount_data.get("raw") == fields["amount_raw"]


def _assert_field_pair(fields: dict[str, object], canonical_key: str, legacy_key: str) -> None:
    assert canonical_key in fields
    assert legacy_key in fields
    assert fields[canonical_key] == fields[legacy_key]


def _assert_amount_fields_as_applicable(fields: dict[str, object]) -> None:
    has_any_amount = any(
        key in fields for key in ["amount", "amount_value", "amount_currency", "amount_raw"]
    )
    if not has_any_amount:
        return

    assert "amount" in fields
    assert isinstance(fields["amount"], dict)

    assert "amount_value" in fields
    assert "amount_raw" in fields
    if fields["amount"].get("currency") not in (None, ""):
        assert "amount_currency" in fields


@pytest.mark.parametrize(
    "filename",
    [
        "01_basic_labelled.txt",
        "02_forwarded_noise.txt",
        "03_missing_fields.txt",
        "04_ambiguous_amounts.txt",
        "05_multiline_weird_spacing.txt",
    ],
)
def test_parse_email_p03_t3_fixtures(filename: str) -> None:
    fixture_text = load_fixture(filename)
    parsed = parse_email(subject="Test", from_addr="sender@example.com", body=fixture_text)

    fields = parsed.fields
    errors = parsed.errors
    error_codes = {error.code for error in errors}

    _assert_alias_consistency(fields)

    if filename == "01_basic_labelled.txt":
        _assert_field_pair(fields, "customer_name", "name")
        _assert_field_pair(fields, "company_name", "company")
        _assert_field_pair(fields, "customer_email", "email")
        _assert_field_pair(fields, "customer_phone", "phone")
        _assert_field_pair(fields, "reference_id", "invoice_or_order_id")
        _assert_amount_fields_as_applicable(fields)
        assert parsed.confidence >= 0.75
        assert len(errors) <= 1

    elif filename == "02_forwarded_noise.txt":
        has_email_phone = ("customer_email" in fields) and ("customer_phone" in fields)
        has_invoice_or_order = "reference_id" in fields
        assert has_email_phone or has_invoice_or_order

        if "customer_email" in fields:
            _assert_field_pair(fields, "customer_email", "email")
        if "customer_phone" in fields:
            _assert_field_pair(fields, "customer_phone", "phone")
        if "reference_id" in fields:
            _assert_field_pair(fields, "reference_id", "invoice_or_order_id")
        _assert_amount_fields_as_applicable(fields)

        assert parsed.confidence >= 0.6

    elif filename == "03_missing_fields.txt":
        assert parsed.confidence <= 0.6
        missing_fields = {error.field for error in errors if error.code == "missing_field"}
        assert "name" in missing_fields
        assert "company" in missing_fields
        assert "invoice_or_order_id" in missing_fields

    elif filename == "04_ambiguous_amounts.txt":
        assert "ambiguous_match" in error_codes
        ambiguous_fields = {error.field for error in errors if error.code == "ambiguous_match"}
        assert "amount" in ambiguous_fields or "invoice_or_order_id" in ambiguous_fields
        _assert_field_pair(fields, "customer_name", "name")
        _assert_field_pair(fields, "company_name", "company")
        _assert_field_pair(fields, "customer_email", "email")
        _assert_field_pair(fields, "customer_phone", "phone")
        _assert_field_pair(fields, "reference_id", "invoice_or_order_id")
        _assert_amount_fields_as_applicable(fields)
        assert parsed.confidence <= 0.85

    elif filename == "05_multiline_weird_spacing.txt":
        _assert_field_pair(fields, "customer_name", "name")
        _assert_field_pair(fields, "customer_email", "email")
        _assert_field_pair(fields, "customer_phone", "phone")
        _assert_field_pair(fields, "reference_id", "invoice_or_order_id")
        _assert_amount_fields_as_applicable(fields)
        assert parsed.confidence >= 0.6
        assert "invalid_format" not in error_codes

    else:
        pytest.fail(f"Unhandled fixture: {filename}")
