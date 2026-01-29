import argparse
import os
from pathlib import Path

from gw_engine.config import ConfigError, load_config
from gw_engine.engine import demo_steps, run_steps


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gw", description="Google Workspace Automation Engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    demo = sub.add_parser("demo", help="Run a placeholder demo workflow (TBD)")
    demo.add_argument("--dry-run", action="store_true", help="Don't call external APIs")

    cfg = sub.add_parser("config", help="Print resolved config (secrets redacted)")
    cfg.add_argument("--profile", choices=["local", "dev", "prod"], help="Override GW_PROFILE")

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
        # optional override
        if args.profile:
            os.environ["GW_PROFILE"] = args.profile
        try:
            cfg_obj = load_config()
        except ConfigError as e:
            raise SystemExit(str(e)) from e
        for k, v in cfg_obj.to_safe_dict().items():
            print(f"{k}={v}")
        return
