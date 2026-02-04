import pytest

from gw_engine.clients import (
    ClientFactoryError,
    scopes_for_api,
    settings_from_env,
)


def test_scopes_drive_oauth_vs_sa() -> None:
    assert scopes_for_api(api="drive", use_service_account=False) == [
        "https://www.googleapis.com/auth/drive.file"
    ]
    assert scopes_for_api(api="drive", use_service_account=True) == [
        "https://www.googleapis.com/auth/drive"
    ]


def test_scopes_sheets_oauth_vs_sa() -> None:
    assert scopes_for_api(api="sheets", use_service_account=False) == [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ]
    assert scopes_for_api(api="sheets", use_service_account=True) == [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]


def test_scopes_gmail_is_readonly() -> None:
    assert scopes_for_api(api="gmail", use_service_account=False) == [
        "https://www.googleapis.com/auth/gmail.readonly"
    ]
    assert scopes_for_api(api="gmail", use_service_account=True) == [
        "https://www.googleapis.com/auth/gmail.readonly"
    ]


def test_settings_from_env_defaults() -> None:
    s = settings_from_env({})
    assert s.timeout_s == 30
    assert s.retry.max_retries == 5


def test_settings_from_env_overrides() -> None:
    s = settings_from_env(
        {
            "GW_HTTP_TIMEOUT_S": "10",
            "GW_HTTP_MAX_RETRIES": "7",
            "GW_HTTP_INITIAL_BACKOFF_S": "0.25",
            "GW_HTTP_MAX_BACKOFF_S": "4.0",
            "GW_HTTP_JITTER_RATIO": "0.1",
        }
    )
    assert s.timeout_s == 10
    assert s.retry.max_retries == 7
    assert s.retry.initial_backoff_s == 0.25
    assert s.retry.max_backoff_s == 4.0
    assert s.retry.jitter_ratio == 0.1


def test_settings_from_env_invalid_int() -> None:
    with pytest.raises(ClientFactoryError):
        settings_from_env({"GW_HTTP_TIMEOUT_S": "nope"})
