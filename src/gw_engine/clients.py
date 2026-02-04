from __future__ import annotations

import json
import os
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, cast

import httplib2
from google.auth.transport.requests import Request
from google.oauth2 import credentials as oauth_credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from gw_engine.config import AppConfig


class DriveService(Protocol):
    def files(self) -> Any: ...


class SheetsService(Protocol):
    def spreadsheets(self) -> Any: ...


class GmailService(Protocol):
    def users(self) -> Any: ...


# ---- Scopes (single source of truth) ----
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

ApiName = Literal["drive", "sheets", "gmail"]


class ClientFactoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class RetryPolicy:
    """
    Simple exponential backoff with jitter.
    - Retries on 429 + selected 5xx
    - Optional 403 rate limit reasons (Google APIs sometimes use 403 for rate limits)
    """

    max_retries: int = 5
    initial_backoff_s: float = 0.5
    max_backoff_s: float = 8.0
    jitter_ratio: float = 0.2  # +/-20%


@dataclass(frozen=True)
class ClientSettings:
    timeout_s: int = 30
    retry: RetryPolicy = RetryPolicy()


def _int_env(env: dict[str, str], key: str, default: int) -> int:
    raw = (env.get(key) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as e:
        raise ClientFactoryError(f"Invalid int env {key}={raw!r}") from e


def _float_env(env: dict[str, str], key: str, default: float) -> float:
    raw = (env.get(key) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as e:
        raise ClientFactoryError(f"Invalid float env {key}={raw!r}") from e


def settings_from_env(env: dict[str, str] | None = None) -> ClientSettings:
    e = env or dict(os.environ)

    timeout_s = _int_env(e, "GW_HTTP_TIMEOUT_S", 30)
    max_retries = _int_env(e, "GW_HTTP_MAX_RETRIES", 5)
    initial_backoff_s = _float_env(e, "GW_HTTP_INITIAL_BACKOFF_S", 0.5)
    max_backoff_s = _float_env(e, "GW_HTTP_MAX_BACKOFF_S", 8.0)
    jitter_ratio = _float_env(e, "GW_HTTP_JITTER_RATIO", 0.2)

    return ClientSettings(
        timeout_s=timeout_s,
        retry=RetryPolicy(
            max_retries=max_retries,
            initial_backoff_s=initial_backoff_s,
            max_backoff_s=max_backoff_s,
            jitter_ratio=jitter_ratio,
        ),
    )


def scopes_for_api(*, api: ApiName, use_service_account: bool) -> list[str]:
    if api == "drive":
        return [DRIVE_SCOPE] if use_service_account else [DRIVE_FILE_SCOPE]
    if api == "sheets":
        # SA often needs Drive scope to access shared files
        return (
            [SHEETS_SCOPE, DRIVE_SCOPE] if use_service_account else [SHEETS_SCOPE, DRIVE_FILE_SCOPE]
        )
    if api == "gmail":
        # In this project: Gmail uses OAuth user creds (dev). SA Gmail needs DWD (future).
        return [GMAIL_READONLY_SCOPE]
    raise ClientFactoryError(f"Unknown api: {api}")


def _service_account_creds(sa_path: str, scopes: list[str]) -> object:
    p = Path(sa_path)
    if not p.exists():
        raise ClientFactoryError(f"Service Account JSON not found: {p}")
    return service_account.Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
        str(p), scopes=scopes
    )


def _oauth_user_creds(cfg: AppConfig, scopes: list[str]) -> object:
    ga = cfg.google_auth
    missing = [
        k
        for k, v in {
            "GOOGLE_CLIENT_ID": ga.client_id,
            "GOOGLE_CLIENT_SECRET": ga.client_secret,
            "GOOGLE_REFRESH_TOKEN": ga.refresh_token,
        }.items()
        if not v
    ]
    if missing:
        raise ClientFactoryError(
            "OAuth user creds not configured.\n"
            f"Missing: {', '.join(missing)}\n"
            "Fix: run `gw auth oauth --client-secrets <file> --scopes <...>` to generate a refresh token,\n"
            "then set env vars in .env (local/dev) or your deployment env (prod).\n"
        )

    creds = oauth_credentials.Credentials(  # type: ignore[no-untyped-call]
        token=None,
        refresh_token=ga.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=ga.client_id,
        client_secret=ga.client_secret,
        scopes=scopes,
    )
    creds.refresh(Request())  # fail fast
    return creds


def _extract_rate_limit_reason(e: HttpError) -> str | None:
    """
    Google APIs may return rate limit signals in 403 bodies:
      reason: rateLimitExceeded / userRateLimitExceeded
    """
    try:
        if not hasattr(e, "content"):
            return None
        raw = e.content.decode("utf-8", errors="ignore")
        data = json.loads(raw)
        err = data.get("error", {})
        errors = err.get("errors", [])
        if errors and isinstance(errors, list) and isinstance(errors[0], dict):
            return str(errors[0].get("reason") or "")
    except Exception:
        return None
    return None


def is_retryable_http_error(e: HttpError) -> bool:
    status = getattr(e.resp, "status", None)
    if status in {429, 500, 502, 503, 504}:
        return True
    if status == 403:
        reason = _extract_rate_limit_reason(e)
        if reason in {"rateLimitExceeded", "userRateLimitExceeded"}:
            return True
    return False


class _ExecRequest(Protocol):
    def execute(self, http: Any | None = None, num_retries: int = 0) -> Any: ...


class _RetryingRequest:
    def __init__(self, inner: _ExecRequest, retry_policy: RetryPolicy) -> None:
        self._inner = inner
        self._policy = retry_policy

    def execute(self, http: Any | None = None, num_retries: int = 0) -> Any:
        policy = self._policy
        attempt = 0
        backoff = policy.initial_backoff_s

        while True:
            try:
                # force underlying request to do 0 internal retries; we own retry loop
                return self._inner.execute(http=http, num_retries=0)
            except HttpError as e:
                attempt += 1
                if attempt > policy.max_retries or not is_retryable_http_error(e):
                    raise

                jitter = 1.0 + random.uniform(-policy.jitter_ratio, policy.jitter_ratio)
                sleep_s = min(policy.max_backoff_s, backoff) * jitter
                time.sleep(max(0.0, sleep_s))
                backoff *= 2.0


def _request_builder(retry_policy: RetryPolicy) -> Callable[..., Any]:
    def builder(
        http: Any,
        postproc: Any,
        uri: str,
        method: str = "GET",
        body: Any = None,
        headers: Any = None,
        methodId: str | None = None,
        resumable: Any = None,
    ) -> Any:
        # Create the real request object using googleapiclient's HttpRequest
        from googleapiclient.http import HttpRequest

        inner = HttpRequest(
            http=http,
            postproc=postproc,
            uri=uri,
            method=method,
            body=body,
            headers=headers,
            methodId=methodId,
            resumable=resumable,
        )
        return _RetryingRequest(inner, retry_policy)

    return builder


@dataclass(frozen=True)
class Services:
    drive: DriveService
    sheets: SheetsService
    gmail: GmailService


def build_service(
    *, cfg: AppConfig, api: ApiName, settings: ClientSettings
) -> DriveService | SheetsService | GmailService:
    use_sa = bool(cfg.google_auth.service_account_json)

    # creds selection
    scopes = scopes_for_api(api=api, use_service_account=use_sa)

    if api == "gmail":
        # always OAuth in this repo (until domain-wide delegation is added)
        creds = _oauth_user_creds(cfg, scopes)
    else:
        if use_sa:
            creds = _service_account_creds(cfg.google_auth.service_account_json or "", scopes)
        else:
            creds = _oauth_user_creds(cfg, scopes)

    # authorized http with timeout
    # NOTE: google-auth-httplib2 is needed for this import.
    from google_auth_httplib2 import AuthorizedHttp  # local import keeps module load clean

    http = AuthorizedHttp(creds, http=httplib2.Http(timeout=settings.timeout_s))

    version = {"drive": "v3", "sheets": "v4", "gmail": "v1"}[api]

    svc = build(
        api,
        version,
        http=http,
        cache_discovery=False,
        requestBuilder=_request_builder(settings.retry),
    )
    if api == "drive":
        return cast(DriveService, svc)
    if api == "sheets":
        return cast(SheetsService, svc)
    return cast(GmailService, svc)


def build_clients(*, cfg: AppConfig, settings: ClientSettings | None = None) -> Services:
    s = settings or settings_from_env()
    return Services(
        drive=cast(DriveService, build_service(cfg=cfg, api="drive", settings=s)),
        sheets=cast(SheetsService, build_service(cfg=cfg, api="sheets", settings=s)),
        gmail=cast(GmailService, build_service(cfg=cfg, api="gmail", settings=s)),
    )
