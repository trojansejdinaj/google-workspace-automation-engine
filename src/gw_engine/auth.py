from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2 import credentials as oauth_credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from gw_engine.config import AppConfig

DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class AuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class Services:
    drive: object | None
    sheets: object | None
    gmail: object | None


def _http_error_hint(e: HttpError) -> str:
    status = getattr(e.resp, "status", None)
    body = ""
    try:
        body = e.content.decode("utf-8", errors="ignore") if hasattr(e, "content") else ""
    except Exception:
        body = ""
    if "storageQuotaExceeded" in body:
        return "SA has no Drive storage; switch SA test to use existing shared sheet (GW_SA_TEST_SHEET_ID) or use Workspace + license/shared drive.\n"
    if status == 403 and (
        "insufficientPermissions" in body or "insufficient authentication scopes" in body
    ):
        return (
            "Missing scopes for this API call.\n"
            "Fix: ensure your requested scopes include what the command needs.\n"
        )
    if status == 401:
        return "Auth failed (401). Fix: refresh token/creds invalid or expired.\n"
    return ""


def _service_account_creds(sa_path: str, scopes: list[str]):
    p = Path(sa_path)
    if not p.exists():
        raise AuthError(f"Service Account JSON not found: {p}")
    return service_account.Credentials.from_service_account_file(str(p), scopes=scopes)


def _oauth_user_creds(cfg: AppConfig, scopes: list[str]):
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
        raise AuthError(
            "OAuth user creds not configured.\n"
            f"Missing: {', '.join(missing)}\n"
            "Fix: run `gw auth oauth --client-secrets <file> --scopes <...>` to generate a refresh token,\n"
            "then set env vars in .env (local/dev) or your deployment env (prod).\n"
        )

    creds = oauth_credentials.Credentials(
        token=None,
        refresh_token=ga.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=ga.client_id,
        client_secret=ga.client_secret,
        scopes=scopes,
    )
    # force refresh so we fail fast with clear errors
    creds.refresh(Request())
    return creds


def build_drive(cfg: AppConfig):
    # OAuth user can stay drive.file if you want
    if cfg.google_auth.service_account_json:
        scopes = [DRIVE_SCOPE]
        creds = _service_account_creds(cfg.google_auth.service_account_json, scopes)
    else:
        scopes = [DRIVE_FILE_SCOPE]
        creds = _oauth_user_creds(cfg, scopes)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def build_sheets(cfg: AppConfig):
    # Sheets needs spreadsheets scope; Drive scope needed for SA access to shared files
    if cfg.google_auth.service_account_json:
        scopes = [SHEETS_SCOPE, DRIVE_SCOPE]
        creds = _service_account_creds(cfg.google_auth.service_account_json, scopes)
    else:
        scopes = [SHEETS_SCOPE, DRIVE_FILE_SCOPE]
        creds = _oauth_user_creds(cfg, scopes)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def build_gmail(cfg: AppConfig):
    """
    Gmail in dev uses OAuth user credentials.
    Service accounts can access Gmail only via Workspace domain-wide delegation (future).
    """
    scopes = [GMAIL_READONLY_SCOPE]

    # Always use OAuth for Gmail if OAuth creds exist.
    # Having a service_account_json configured for Drive/Sheets should NOT block Gmail.
    creds = _oauth_user_creds(cfg, scopes)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def oauth_dev_flow(*, client_secrets_path: Path, scopes: list[str]) -> str:
    if not client_secrets_path.exists():
        raise AuthError(f"Client secrets file not found: {client_secrets_path}")
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), scopes=scopes)
    creds = flow.run_local_server(port=0, prompt="consent")
    if not creds.refresh_token:
        raise AuthError(
            "No refresh token returned.\n"
            "Fix: re-run and ensure prompt='consent' is used, and you haven't previously authorized without offline access.\n"
        )
    return creds.refresh_token


def test_service_account_drive_sheets(cfg: AppConfig) -> str:
    """
    Quota-safe SA test:
    - uses an existing spreadsheet you created (owned by you)
    - spreadsheet must be shared with the service account (Editor)
    - SA reads sheet + writes a cell + reads back
    """
    import os

    sheet_id = os.getenv("GW_SA_TEST_SHEET_ID", "").strip()
    if not sheet_id:
        raise AuthError(
            "GW_SA_TEST_SHEET_ID is not set.\n"
            "Fix: create a spreadsheet in your Drive, share it with the service account email (Editor),\n"
            "then set GW_SA_TEST_SHEET_ID=<spreadsheet_id>."
        )

    try:
        drive = build_drive(cfg)
        sheets = build_sheets(cfg)

        # Drive: prove SA can see the file
        meta = drive.files().get(fileId=sheet_id, fields="id,name").execute()

        # Sheets: prove SA can read
        _ = sheets.spreadsheets().get(spreadsheetId=sheet_id).execute()

        # Sheets: prove SA can write (no new file creation)
        sheets.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range="A1",
            valueInputOption="RAW",
            body={"values": [["sa-ok"]]},
        ).execute()

        # Sheets: read back
        val = (
            sheets.spreadsheets()
            .values()
            .get(
                spreadsheetId=sheet_id,
                range="A1",
            )
            .execute()
            .get("values", [[""]])[0][0]
        )

        return (
            "Service Account OK: Drive get + Sheets read/write succeeded.\n"
            f"file={meta.get('name')} ({meta.get('id')})\n"
            f"A1={val}"
        )

    except HttpError as e:
        raise AuthError(str(e) + "\n" + _http_error_hint(e)) from e


def test_oauth_gmail(cfg: AppConfig) -> str:
    try:
        gmail = build_gmail(cfg)
        prof = gmail.users().getProfile(userId="me").execute()
        # prof includes emailAddress, messagesTotal, threadsTotal, historyId
        return f"OAuth OK: Gmail profile for {prof.get('emailAddress')}"
    except HttpError as e:
        raise AuthError(str(e) + "\n" + _http_error_hint(e)) from e
