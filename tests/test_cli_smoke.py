from gw_engine.cli import build_parser


def test_cli_has_demo_command() -> None:
    parser = build_parser()
    # should parse without error
    args = parser.parse_args(["demo", "--dry-run"])
    assert args.cmd == "demo"
    assert args.dry_run is True
