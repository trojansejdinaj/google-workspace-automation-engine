from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


class ConfigError(RuntimeError):
    pass


PROFILE_VALUES = ("local", "dev", "prod")


def _read_dotenv_file(path: Path) -> dict[str, str]:
    """
    Minimal dotenv reader:
    - supports KEY=VALUE
    - ignores empty lines + comments starting with #
    - does not expand variables (keep it deterministic)
    """
    data: dict[str, str] = {}
    if not path.exists():
        return data

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip().strip('"').strip("'")
        if key:
            data[key] = val
    return data


def _merge_env(base: Mapping[str, str], overlay: Mapping[str, str]) -> dict[str, str]:
    merged = dict(base)
    merged.update({k: v for k, v in overlay.items() if v is not None})
    return merged


def _get_profile(env: Mapping[str, str]) -> str:
    profile = (env.get("GW_PROFILE") or "local").strip().lower()
    if profile not in PROFILE_VALUES:
        raise ConfigError(
            f"Invalid GW_PROFILE='{profile}'. Expected one of: {', '.join(PROFILE_VALUES)}"
        )
    return profile


def _as_bool(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def _required(env: Mapping[str, str], keys: list[str], *, profile: str) -> dict[str, str]:
    missing = [k for k in keys if not (env.get(k) or "").strip()]
    if missing:
        hint = (
            "Missing required config values for profile "
            f"'{profile}': {', '.join(missing)}\n"
            "Fix:\n"
            "  1) Copy .env.example -> .env (local/dev)\n"
            "  2) Or set env vars in your deployment (prod)\n"
            "  3) Re-run the command\n"
        )
        raise ConfigError(hint)
    return {k: env[k].strip() for k in keys}


@dataclass(frozen=True)
class GoogleAuthConfig:
    # Choose one:
    # - service account: GOOGLE_SERVICE_ACCOUNT_JSON (path)
    # - OAuth client: GOOGLE_CLIENT_ID/SECRET + GOOGLE_REFRESH_TOKEN
    service_account_json: str | None
    client_id: str | None
    client_secret: str | None
    refresh_token: str | None

    def validate(self, *, profile: str) -> None:
        sa = (self.service_account_json or "").strip()
        oauth = all(
            (self.client_id or "").strip()
            and (self.client_secret or "").strip()
            and (self.refresh_token or "").strip()
            for _ in [0]
        )

        if profile == "prod":
            # In prod, require one auth method to be fully configured.
            if not sa and not oauth:
                raise ConfigError(
                    "Prod auth is not configured.\n"
                    "Provide either:\n"
                    "  - GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service_account.json\n"
                    "or:\n"
                    "  - GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN\n"
                )

        # In local/dev we allow incomplete auth early (because T3+ will use it),
        # but config should still be parseable.


@dataclass(frozen=True)
class AppConfig:
    profile: str
    debug: bool
    log_level: str
    runs_dir: Path
    google_auth: GoogleAuthConfig

    def to_safe_dict(self) -> dict[str, str]:
        def red(v: str | None) -> str:
            if not v:
                return ""
            # show only prefix/suffix to prove it's set without leaking it
            s = v.strip()
            if len(s) <= 8:
                return "********"
            return f"{s[:3]}...{s[-3:]}"

        return {
            "GW_PROFILE": self.profile,
            "GW_DEBUG": str(self.debug),
            "GW_LOG_LEVEL": self.log_level,
            "GW_RUNS_DIR": str(self.runs_dir),
            "GOOGLE_SERVICE_ACCOUNT_JSON": self.google_auth.service_account_json or "",
            "GOOGLE_CLIENT_ID": red(self.google_auth.client_id),
            "GOOGLE_CLIENT_SECRET": red(self.google_auth.client_secret),
            "GOOGLE_REFRESH_TOKEN": red(self.google_auth.refresh_token),
        }


def load_config(
    *,
    env: Mapping[str, str] | None = None,
    base_dir: Path | None = None,
) -> AppConfig:
    """
    Loads config with profile support.

    Priority:
      1) OS env
      2) .env (if exists)
      3) .env.<profile> (if exists) overrides .env

    NOTE: dotenv files are only read to populate *missing* env vars (we don't overwrite OS env).
    """
    env0: Mapping[str, str] = env or os.environ
    profile = _get_profile(env0)

    root = base_dir or Path.cwd()

    dotenv_base = _read_dotenv_file(root / ".env")
    dotenv_profile = _read_dotenv_file(root / f".env.{profile}")

    # OS env wins; dotenv fills gaps.
    merged = dict(env0)
    for k, v in _merge_env(dotenv_base, dotenv_profile).items():
        merged.setdefault(k, v)

    debug = _as_bool(merged.get("GW_DEBUG"), default=(profile != "prod"))
    log_level = (merged.get("GW_LOG_LEVEL") or ("INFO" if profile == "prod" else "DEBUG")).strip()

    runs_dir = Path((merged.get("GW_RUNS_DIR") or "runs").strip())

    google_auth = GoogleAuthConfig(
        service_account_json=(merged.get("GOOGLE_SERVICE_ACCOUNT_JSON") or "").strip() or None,
        client_id=(merged.get("GOOGLE_CLIENT_ID") or "").strip() or None,
        client_secret=(merged.get("GOOGLE_CLIENT_SECRET") or "").strip() or None,
        refresh_token=(merged.get("GOOGLE_REFRESH_TOKEN") or "").strip() or None,
    )

    # Validation: prod must be properly configured; local/dev parse cleanly.
    google_auth.validate(profile=profile)

    # Secrets hygiene: ensure we never require secrets to be committed.
    # But we *do* enforce that .env.example exists for local/dev guidance (optional check).
    if profile in {"local", "dev"}:
        example_path = root / ".env.example"
        if not example_path.exists():
            raise ConfigError("Missing .env.example. Add it so local/dev setup is obvious.")

    return AppConfig(
        profile=profile,
        debug=debug,
        log_level=log_level,
        runs_dir=runs_dir,
        google_auth=google_auth,
    )
