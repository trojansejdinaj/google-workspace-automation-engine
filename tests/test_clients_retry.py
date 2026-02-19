"""Tests for client retry logic with APIRetryExhausted exception handling."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from gw_engine.clients import ClientSettings, RetryPolicy, _RetryingRequest
from gw_engine.exceptions import APIRetryExhausted


class FakeHttpError(Exception):
    """Fake HttpError-like exception for testing."""

    def __init__(self, status_code: int, reason: str | None = None):
        self.resp = Mock()
        self.resp.status = status_code
        self.resp.reason = reason or f"Error {status_code}"

        # Add content attribute with JSON body for 403 rate limit extraction
        if status_code == 403 and reason:
            import json

            self.content = json.dumps({"error": {"errors": [{"reason": reason}]}}).encode("utf-8")
        else:
            self.content = b""

        super().__init__(f"HttpError {status_code}")


class FakeRequest:
    """Fake inner request that can fail N times then succeed."""

    def __init__(self, fail_count: int, status_code: int):
        self.fail_count = fail_count
        self.status_code = status_code
        self.call_count = 0
        self.result = {"success": True}

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        self.call_count += 1
        if self.call_count <= self.fail_count:
            raise FakeHttpError(self.status_code)
        return self.result


def test_retry_on_429_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that 429 errors trigger retries and eventually succeed."""
    # Monkeypatch time.sleep to avoid real waiting
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("time.sleep", fake_sleep)

    # Patch HttpError in clients module to use our FakeHttpError
    monkeypatch.setattr("gw_engine.clients.HttpError", FakeHttpError)

    # Create fake request that fails 2 times with 429, then succeeds
    fake_inner = FakeRequest(fail_count=2, status_code=429)

    # Create retrying request with small retry config
    retry_policy = RetryPolicy(
        max_retries=5, initial_backoff_s=0.1, max_backoff_s=1.0, jitter_ratio=0.05
    )
    settings = ClientSettings(retry=retry_policy, log_retry=False)

    retrying = _RetryingRequest(
        inner=fake_inner,
        retry_policy=settings.retry,
        log_retry=settings.log_retry,
        log_sink=settings.log_sink,
        operation="test.operation",
    )

    # Execute should succeed after retries
    result = retrying.execute()

    assert result == {"success": True}
    assert fake_inner.call_count == 3  # 2 failures + 1 success
    assert len(sleep_calls) == 2  # Slept twice before retries


def test_retry_on_500_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that 500 errors trigger retries and eventually succeed."""
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("time.sleep", fake_sleep)

    # Patch HttpError in clients module
    monkeypatch.setattr("gw_engine.clients.HttpError", FakeHttpError)

    # Create fake request that fails 1 time with 500, then succeeds
    fake_inner = FakeRequest(fail_count=1, status_code=500)

    retry_policy = RetryPolicy(
        max_retries=5, initial_backoff_s=0.1, max_backoff_s=1.0, jitter_ratio=0.05
    )
    settings = ClientSettings(retry=retry_policy, log_retry=False)

    retrying = _RetryingRequest(
        inner=fake_inner,
        retry_policy=settings.retry,
        log_retry=settings.log_retry,
        log_sink=settings.log_sink,
        operation="test.operation",
    )

    result = retrying.execute()

    assert result == {"success": True}
    assert fake_inner.call_count == 2  # 1 failure + 1 success
    assert len(sleep_calls) == 1  # Slept once


def test_retry_on_503_service_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that 503 errors trigger retries and eventually succeed."""
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("time.sleep", fake_sleep)

    # Patch HttpError in clients module
    monkeypatch.setattr("gw_engine.clients.HttpError", FakeHttpError)

    # Create fake request that fails 1 time with 503, then succeeds
    fake_inner = FakeRequest(fail_count=1, status_code=503)

    retry_policy = RetryPolicy(
        max_retries=5, initial_backoff_s=0.1, max_backoff_s=1.0, jitter_ratio=0.05
    )
    settings = ClientSettings(retry=retry_policy, log_retry=False)

    retrying = _RetryingRequest(
        inner=fake_inner,
        retry_policy=settings.retry,
        log_retry=settings.log_retry,
        log_sink=settings.log_sink,
        operation="test.operation",
    )

    result = retrying.execute()

    assert result == {"success": True}
    assert fake_inner.call_count == 2


def test_no_retry_on_400_bad_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that 400 errors do NOT trigger retries."""
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("time.sleep", fake_sleep)

    # Patch HttpError in clients module

    monkeypatch.setattr("gw_engine.clients.HttpError", FakeHttpError)

    # Create fake request that always fails with 400
    fake_inner = FakeRequest(fail_count=999, status_code=400)

    retry_policy = RetryPolicy(
        max_retries=5, initial_backoff_s=0.1, max_backoff_s=1.0, jitter_ratio=0.05
    )
    settings = ClientSettings(retry=retry_policy, log_retry=False)

    retrying = _RetryingRequest(
        inner=fake_inner,
        retry_policy=settings.retry,
        log_retry=settings.log_retry,
        log_sink=settings.log_sink,
        operation="test.operation",
    )

    # Should raise immediately without retries
    with pytest.raises(FakeHttpError) as exc_info:
        retrying.execute()

    assert exc_info.value.resp.status == 400
    assert fake_inner.call_count == 1  # Only tried once
    assert len(sleep_calls) == 0  # Never slept


def test_retry_exhausted_raises_api_retry_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that exhausting retries raises APIRetryExhausted with correct fields."""
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("time.sleep", fake_sleep)

    # Patch HttpError in clients module

    monkeypatch.setattr("gw_engine.clients.HttpError", FakeHttpError)

    # Create fake request that always fails with 429
    fake_inner = FakeRequest(fail_count=999, status_code=429)

    retry_policy = RetryPolicy(
        max_retries=3, initial_backoff_s=0.1, max_backoff_s=1.0, jitter_ratio=0.05
    )
    settings = ClientSettings(retry=retry_policy, log_retry=False)

    retrying = _RetryingRequest(
        inner=fake_inner,
        retry_policy=settings.retry,
        log_retry=settings.log_retry,
        log_sink=settings.log_sink,
        operation="sheets.spreadsheets.values.get",
    )

    # Should raise APIRetryExhausted after max_retries
    with pytest.raises(APIRetryExhausted) as exc_info:
        retrying.execute()

    exc = exc_info.value
    assert exc.operation == "sheets.spreadsheets.values.get"
    assert exc.attempts == 4  # 1 initial + 3 retries
    assert exc.status_code == 429
    assert exc.reason is None  # reason only extracted for 403 errors
    assert "APIRetryExhausted" in str(exc)
    assert "sheets.spreadsheets.values.get" in str(exc)

    assert fake_inner.call_count == 4  # Tried 1 + max_retries times
    assert len(sleep_calls) == 3  # Slept between attempts (3 times for 4 attempts)


def test_retry_with_403_rate_limit_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that 403 errors with rateLimitExceeded reason are retried."""
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("time.sleep", fake_sleep)

    # Patch HttpError in clients module
    monkeypatch.setattr("gw_engine.clients.HttpError", FakeHttpError)

    # Create fake request that fails with 403 rateLimitExceeded
    class FakeRequest403:
        def __init__(self) -> None:
            self.call_count = 0

        def execute(self, **kwargs: Any) -> dict[str, Any]:
            self.call_count += 1
            if self.call_count <= 2:
                error = FakeHttpError(403, reason="rateLimitExceeded")
                raise error
            return {"success": True}

    fake_inner = FakeRequest403()

    retry_policy = RetryPolicy(
        max_retries=5, initial_backoff_s=0.1, max_backoff_s=1.0, jitter_ratio=0.05
    )
    settings = ClientSettings(retry=retry_policy, log_retry=False)

    retrying = _RetryingRequest(
        inner=fake_inner,
        retry_policy=settings.retry,
        log_retry=settings.log_retry,
        log_sink=settings.log_sink,
        operation="test.operation",
    )

    result = retrying.execute()

    assert result == {"success": True}
    assert fake_inner.call_count == 3
    assert len(sleep_calls) == 2


def test_retry_logging_emits_structured_events(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that retry logging emits structured log events."""
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("time.sleep", fake_sleep)

    # Patch HttpError in clients module
    monkeypatch.setattr("gw_engine.clients.HttpError", FakeHttpError)

    # Capture log events
    log_events: list[dict[str, Any]] = []

    def log_sink(event: dict[str, Any]) -> None:
        log_events.append(event)

    # Create fake request that fails 2 times with 429
    fake_inner = FakeRequest(fail_count=2, status_code=429)

    retry_policy = RetryPolicy(
        max_retries=5, initial_backoff_s=0.1, max_backoff_s=1.0, jitter_ratio=0.05
    )
    settings = ClientSettings(retry=retry_policy, log_retry=True, log_sink=log_sink)

    retrying = _RetryingRequest(
        inner=fake_inner,
        retry_policy=settings.retry,
        log_retry=settings.log_retry,
        log_sink=settings.log_sink,
        operation="sheets.spreadsheets.get",
    )

    result = retrying.execute()

    assert result == {"success": True}

    # Should have 2 api_retry events (one for each failure)
    retry_events = [e for e in log_events if e.get("event") == "api_retry"]
    assert len(retry_events) == 2

    # Verify first retry event structure
    first_retry = retry_events[0]
    assert first_retry["event"] == "api_retry"
    assert first_retry["operation"] == "sheets.spreadsheets.get"
    assert first_retry["attempt"] == 1
    assert first_retry["max_retries"] == 5
    assert first_retry["status_code"] == 429
    assert "sleep_s" in first_retry
    assert isinstance(first_retry["sleep_s"], float)

    # Verify second retry event
    second_retry = retry_events[1]
    assert second_retry["attempt"] == 2


def test_retry_exhausted_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that exhausted retries emit api_retry_exhausted event."""
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("time.sleep", fake_sleep)

    # Patch HttpError in clients module
    monkeypatch.setattr("gw_engine.clients.HttpError", FakeHttpError)

    # Capture log events
    log_events: list[dict[str, Any]] = []

    def log_sink(event: dict[str, Any]) -> None:
        log_events.append(event)

    # Create fake request that always fails
    fake_inner = FakeRequest(fail_count=999, status_code=503)

    retry_policy = RetryPolicy(
        max_retries=3, initial_backoff_s=0.1, max_backoff_s=1.0, jitter_ratio=0.05
    )
    settings = ClientSettings(retry=retry_policy, log_retry=True, log_sink=log_sink)

    retrying = _RetryingRequest(
        inner=fake_inner,
        retry_policy=settings.retry,
        log_retry=settings.log_retry,
        log_sink=settings.log_sink,
        operation="drive.files.list",
    )

    with pytest.raises(APIRetryExhausted):
        retrying.execute()

    # Should have both api_retry and api_retry_exhausted events
    retry_events = [e for e in log_events if e.get("event") == "api_retry"]
    exhausted_events = [e for e in log_events if e.get("event") == "api_retry_exhausted"]

    assert len(retry_events) == 3  # Retried 3 times (attempts 1, 2, 3)
    assert len(exhausted_events) == 1

    # Verify exhausted event structure
    exhausted = exhausted_events[0]
    assert exhausted["event"] == "api_retry_exhausted"
    assert exhausted["operation"] == "drive.files.list"
    assert exhausted["attempt"] == 4  # Final attempt that exhausted retries
    assert exhausted["max_retries"] == 3
    assert exhausted["status_code"] == 503
    assert "error_message" in exhausted
