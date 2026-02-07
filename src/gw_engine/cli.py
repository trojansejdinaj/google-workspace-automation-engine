import argparse
import json
import os
from pathlib import Path
from typing import Any, cast

from gw_engine.auth import (
    AuthError,
    oauth_dev_flow,
    test_oauth_gmail,
    test_service_account_drive_sheets,
)
from gw_engine.config import ConfigError, load_config
from gw_engine.contracts import RunState, Step, StepResult
from gw_engine.engine import run_steps_result
from gw_engine.exporters import ExportError, export_run_audit
from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext

_SCOPE_MAP = {
    "gmail.readonly": "https://www.googleapis.com/auth/gmail.readonly",
    "drive.file": "https://www.googleapis.com/auth/drive.file",
    "spreadsheets": "https://www.googleapis.com/auth/spreadsheets",
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gw", description="Google Workspace Automation Engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    # demo
    demo = sub.add_parser("demo", help="Run deterministic end-to-end engine demo")
    demo.add_argument(
        "--dry-run",
        action="store_true",
        help="Compatibility flag (demo already runs locally without external APIs)",
    )

    # config
    cfg = sub.add_parser("config", help="Print resolved config (secrets redacted)")
    cfg.add_argument("--profile", choices=["local", "dev", "prod"], help="Override GW_PROFILE")

    # export
    export = sub.add_parser("export", help="Export audit data for an existing run_id")
    export.add_argument("run_id", help="Run identifier under runs/<run_id>/")
    export.add_argument("--format", choices=["json", "csv"], default="json", help="Export format")
    export.add_argument("--out", help="Optional output path (defaults under runs/<run_id>/)")

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


def demo_steps() -> list[Step]:
    def build_payload(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        payload: dict[str, Any] = {
            "message": "gw demo payload",
            "run_id": ctx.run_id,
            "version": 1,
        }
        state.data["demo_payload"] = payload
        log.info(
            "demo_payload_built",
            run_id=ctx.run_id,
            step="build_payload",
            payload_keys=list(payload.keys()),
        )
        return StepResult(ok=True, outputs={"payload_keys": len(payload)})

    def write_artifact(ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        payload_raw = state.data.get("demo_payload")
        if not isinstance(payload_raw, dict):
            return StepResult(ok=False, error="missing demo payload from prior step")

        payload = cast(dict[str, Any], payload_raw)
        artifacts_dir = ctx.run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifacts_dir / "demo_payload.json"
        artifact_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        artifact_rel = artifact_path.relative_to(ctx.run_dir).as_posix()
        log.info(
            "demo_artifact_written",
            run_id=ctx.run_id,
            step="write_artifact",
            artifact=artifact_rel,
        )
        return StepResult(ok=True, outputs={"artifact": artifact_rel})

    return [
        Step(name="build_payload", fn=build_payload),
        Step(name="write_artifact", fn=write_artifact),
    ]


def _print_demo_banner(
    *,
    status: str,
    run_id: str,
    run_dir: Path,
    logs_path: Path,
    audit_json_path: Path | None,
    audit_csv_path: Path | None,
    error: str | None = None,
) -> None:
    print("=== GW DEMO RESULT ===")
    print(f"status={status}")
    print(f"run_id={run_id}")
    print(f"run_dir={run_dir}")
    print(f"logs={logs_path}")
    print(f"audit_json={audit_json_path or 'n/a'}")
    print(f"audit_csv={audit_csv_path or 'n/a'}")
    if error:
        print(f"error={error}")
    print("======================")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "demo":
        try:
            cfg = load_config()
        except ConfigError as e:
            raise SystemExit(str(e)) from e

        ctx, result = run_steps_result(runs_dir=Path(cfg.runs_dir), steps=demo_steps())
        status = "OK" if result.ok else "FAILED"
        run_error = (
            f"failed_step={result.failed_step} error={result.error}" if not result.ok else None
        )

        audit_json_path: Path | None = None
        audit_csv_path: Path | None = None
        export_error: str | None = None
        try:
            audit_json_path = export_run_audit(
                runs_dir=Path(cfg.runs_dir),
                run_id=ctx.run_id,
                fmt="json",
            )
            audit_csv_path = export_run_audit(
                runs_dir=Path(cfg.runs_dir),
                run_id=ctx.run_id,
                fmt="csv",
            )
        except ExportError as e:
            status = "FAILED"
            export_error = str(e)

        _print_demo_banner(
            status=status,
            run_id=ctx.run_id,
            run_dir=ctx.run_dir,
            logs_path=ctx.logs_path,
            audit_json_path=audit_json_path,
            audit_csv_path=audit_csv_path,
            error=export_error or run_error,
        )
        if export_error:
            raise SystemExit(export_error)
        if run_error:
            raise SystemExit(run_error)
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

    if args.cmd == "export":
        try:
            cfg = load_config()
        except ConfigError as e:
            raise SystemExit(str(e)) from e

        try:
            out_path = export_run_audit(
                runs_dir=Path(cfg.runs_dir),
                run_id=args.run_id,
                fmt=args.format,
                out_path=Path(args.out) if args.out else None,
            )
            print(f"audit={out_path}")
            return
        except ExportError as e:
            raise SystemExit(str(e)) from e

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
