from __future__ import annotations

from types import SimpleNamespace

import pytest

from gw_engine.retry import _extract_status_code


class StatusCodeError(Exception):
    def __init__(self, status_code: object) -> None:
        self.status_code = status_code


class RespStatusError(Exception):
    def __init__(self, status: object) -> None:
        self.resp = SimpleNamespace(status=status)


class StatusError(Exception):
    def __init__(self, status: object) -> None:
        self.status = status


@pytest.mark.parametrize("value", [429, 500])
def test_extract_status_code_accepts_exact_int_values(value: int) -> None:
    assert _extract_status_code(StatusCodeError(value)) == value
    assert _extract_status_code(RespStatusError(value)) == value
    assert _extract_status_code(StatusError(value)) == value


@pytest.mark.parametrize("value", [True, False])
def test_extract_status_code_rejects_bool_values(value: bool) -> None:
    assert _extract_status_code(StatusCodeError(value)) is None
    assert _extract_status_code(RespStatusError(value)) is None
    assert _extract_status_code(StatusError(value)) is None


@pytest.mark.parametrize("value", ["429", None])
def test_extract_status_code_returns_none_for_invalid_status_values(value: object) -> None:
    assert _extract_status_code(StatusCodeError(value)) is None
    assert _extract_status_code(RespStatusError(value)) is None
    assert _extract_status_code(StatusError(value)) is None
