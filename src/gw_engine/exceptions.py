"""Typed exceptions for the Google Workspace automation engine."""

from __future__ import annotations

from typing import Any


class APIRetryExhausted(RuntimeError):
    """Raised when API retry attempts are exhausted.

    This exception indicates that a transient API error (e.g., rate limit or
    server error) persisted across all retry attempts.
    """

    def __init__(
        self,
        operation: str,
        attempts: int,
        status_code: int | None = None,
        reason: str | None = None,
        message: str | None = None,
        cause: Exception | None = None,
    ):
        """Initialize APIRetryExhausted exception.

        Args:
            operation: Operation name that failed
            attempts: Number of attempts made
            status_code: HTTP status code if known
            reason: Rate limit reason (e.g., 'rateLimitExceeded') for 403 errors
            message: Optional custom error message
            cause: Original exception that caused the failure
        """
        self.operation = operation
        self.attempts = attempts
        self.status_code = status_code
        self.reason = reason
        self.message = message or "API retry attempts exhausted"
        self.cause = cause
        super().__init__(str(self))

    def __str__(self) -> str:
        """Format exception as human-readable string."""
        parts = [f"APIRetryExhausted: {self.message}"]
        parts.append(f"operation={self.operation}")
        parts.append(f"attempts={self.attempts}")
        if self.status_code is not None:
            parts.append(f"status_code={self.status_code}")
        if self.reason is not None:
            parts.append(f"reason={self.reason}")
        return " | ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Serialize exception to dictionary for logging/export.

        Returns:
            Dictionary with exception details
        """
        result: dict[str, Any] = {
            "error_type": "APIRetryExhausted",
            "operation": self.operation,
            "attempts": self.attempts,
            "message": self.message,
        }
        if self.status_code is not None:
            result["status_code"] = self.status_code
        if self.reason is not None:
            result["reason"] = self.reason
        if self.cause is not None:
            result["cause"] = str(self.cause)
            result["cause_type"] = type(self.cause).__name__
        return result
