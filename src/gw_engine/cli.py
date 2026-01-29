import argparse


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gw", description="Google Workspace Automation Engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    demo = sub.add_parser("demo", help="Run a placeholder demo workflow (TBD)")
    demo.add_argument("--dry-run", action="store_true", help="Don't call external APIs")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "demo":
        print("gw demo: placeholder (coming soon)")
        return
