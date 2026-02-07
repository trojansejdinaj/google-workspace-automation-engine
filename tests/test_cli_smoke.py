from gw_engine.cli import build_parser


def test_cli_has_demo_command() -> None:
    parser = build_parser()
    # should parse without error
    args = parser.parse_args(["demo", "--dry-run"])
    assert args.cmd == "demo"
    assert args.dry_run is True


def test_cli_has_export_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["export", "abc123", "--format", "csv", "--out", "out.csv"])
    assert args.cmd == "export"
    assert args.run_id == "abc123"
    assert args.format == "csv"
    assert args.out == "out.csv"
