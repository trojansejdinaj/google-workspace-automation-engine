"""Retry framework for transient HTTP API errors.

Provides exponential backoff with jitter for handling rate limits (429)
and transient server errors (5xx).
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from gw_engine.exceptions import APIRetryExhausted


@dataclass
class RetryConfig:
    """Configuration for retry behavior with exponential backoff."""

    max_attempts: int = 5
    base_delay_s: float = 0.5
    max_delay_s: float = 8.0
    jitter_s: float = 0.2


def is_retryable_status(status_code: int) -> bool:
    """Check if an HTTP status code is retryable.

    Args:
        status_code: HTTP status code

    Returns:
        True if status is 429 (rate limit) or 5xx (server error)
    """
    return status_code == 429 or 500 <= status_code <= 599


def compute_backoff_s(attempt: int, cfg: RetryConfig) -> float:
    """Compute exponential backoff delay with jitter.

    Args:
        attempt: Current attempt number (1-indexed)
        cfg: Retry configuration

    Returns:
        Delay in seconds before next retry
    """
    # Exponential backoff: base * 2^(attempt-1)
    delay = cfg.base_delay_s * (2 ** (attempt - 1))

    # Clamp to max
    delay = min(delay, cfg.max_delay_s)

    # Add random jitter
    jitter = random.uniform(0, cfg.jitter_s)

    return delay + jitter


def _extract_status_code(exc: Exception) -> int | None:
    """Extract HTTP status code from various exception types.

    Supports:
    - exc.status_code (common pattern)
    - exc.resp.status (googleapiclient HttpError)
    - exc.status (alternative pattern)

    Args:
        exc: Exception that may contain status code

    Returns:
        Status code if found, None otherwise
    """
    # Try direct status_code attribute
    if hasattr(exc, "status_code"):
        return exc.status_code  # type: ignore[return-value]

    # Try resp.status (googleapiclient HttpError pattern)
    if hasattr(exc, "resp") and hasattr(exc.resp, "status"):
        return exc.resp.status  # type: ignore[return-value, attr-defined]

    # Try direct status attribute
    if hasattr(exc, "status"):
        return exc.status  # type: ignore[return-value]

    return None


def with_retries[T](
    callable_fn: Callable[[], T],
    *,
    operation: str,
    logger: Any,
    cfg: RetryConfig,
    context: dict[str, Any] | None = None,
) -> T:
    """Execute a callable with automatic retries on transient errors.

    Args:
        callable_fn: Function to execute (takes no args)
        operation: Operation name for logging
        logger: Logger instance with info() method
        cfg: Retry configuration
        context: Optional extra fields to include in log events

    Returns:
        Result from callable_fn()

    Raises:
        APIRetryExhausted: If all retry attempts fail
        Exception: Non-retryable errors are raised immediately
    """
    context = context or {}
    last_error: Exception | None = None
    last_status: int | None = None

    for attempt in range(1, cfg.max_attempts + 1):
        try:
            return callable_fn()
        except Exception as exc:
            last_error = exc
            status_code = _extract_status_code(exc)
            last_status = status_code

            # Check if error is retryable
            if status_code is None or not is_retryable_status(status_code):
                # Non-retryable error, raise immediately
                raise

            # Last attempt failed, don't retry
            if attempt >= cfg.max_attempts:
                break

            # Compute backoff and log retry
            sleep_s = compute_backoff_s(attempt, cfg)

            log_fields = {
                "event": "api_retry",
                "operation": operation,
                "attempt": attempt,
                "max_attempts": cfg.max_attempts,
                "sleep_s": round(sleep_s, 3),
                "status_code": status_code,
                **context,
            }
            logger.info(**log_fields)

            # Sleep before retry
            time.sleep(sleep_s)

    # All attempts exhausted
    raise APIRetryExhausted(
        operation=operation,
        attempts=cfg.max_attempts,
        status_code=last_status,
        message=f"Failed after {cfg.max_attempts} attempts",
        cause=last_error,
    )
