import argparse
import os
from pathlib import Path

from gw_engine.auth import (
    AuthError,
    oauth_dev_flow,
    test_oauth_gmail,
    test_service_account_drive_sheets,
)
from gw_engine.config import ConfigError, load_config
from gw_engine.engine import demo_steps, run_steps

_SCOPE_MAP = {
    "gmail.readonly": "https://www.googleapis.com/auth/gmail.readonly",
    "drive.file": "https://www.googleapis.com/auth/drive.file",
    "spreadsheets": "https://www.googleapis.com/auth/spreadsheets",
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gw", description="Google Workspace Automation Engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    # demo
    demo = sub.add_parser("demo", help="Run a placeholder demo workflow (TBD)")
    demo.add_argument("--dry-run", action="store_true", help="Don't call external APIs")

    # config
    cfg = sub.add_parser("config", help="Print resolved config (secrets redacted)")
    cfg.add_argument("--profile", choices=["local", "dev", "prod"], help="Override GW_PROFILE")

    # auth
    auth = sub.add_parser("auth", help="Auth helpers (dev)")
    auth_sub = auth.add_subparsers(dest="auth_cmd", required=True)

    oauth = auth_sub.add_parser("oauth", help="Run OAuth dev flow and print refresh token")
    oauth.add_argument("--client-secrets", required=True, help="Path to OAuth client secrets JSON")
    oauth.add_argument(
        "--scopes",
        nargs="+",
        default=["gmail.readonly"],
        help="Scopes (short names like gmail.readonly/drive.file/spreadsheets OR full URIs)",
    )
    oauth.add_argument(
        "--out",
        help="Optional path to write token (recommended under runs/ which is ignored)",
    )

    test = auth_sub.add_parser("test", help="Test auth")
    test.add_argument(
        "target",
        choices=["sa", "gmail"],
        help="sa=Drive+Sheets via service account, gmail=OAuth dev",
    )

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "demo":
        try:
            cfg = load_config()
        except ConfigError as e:
            raise SystemExit(str(e)) from e

        ctx = run_steps(runs_dir=Path(cfg.runs_dir), steps=demo_steps())
        print(f"run_id={ctx.run_id}")
        print(f"logs={ctx.logs_path}")
        return

    if args.cmd == "config":
        if args.profile:
            os.environ["GW_PROFILE"] = args.profile
        try:
            cfg_obj = load_config()
        except ConfigError as e:
            raise SystemExit(str(e)) from e

        for k, v in cfg_obj.to_safe_dict().items():
            print(f"{k}={v}")
        return

    if args.cmd == "auth":
        # profile override is useful here too (optional)
        # (kept simple: use GW_PROFILE env like other commands)
        try:
            cfg = load_config()
        except ConfigError as e:
            raise SystemExit(str(e)) from e

        try:
            if args.auth_cmd == "oauth":
                scopes = [_SCOPE_MAP.get(s, s) for s in args.scopes]
                token = oauth_dev_flow(client_secrets_path=Path(args.client_secrets), scopes=scopes)

                if args.out:
                    out_path = Path(args.out)
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(token + "\n", encoding="utf-8")
                    print(f"refresh_token_written_to={out_path}")

                print(f"refresh_token={token}")
                return

            if args.auth_cmd == "test":
                if args.target == "sa":
                    print(test_service_account_drive_sheets(cfg))
                    return
                if args.target == "gmail":
                    print(test_oauth_gmail(cfg))
                    return

        except AuthError as e:
            raise SystemExit(str(e)) from e
