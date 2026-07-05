from scripts.run_voice_control import build_arg_parser


def test_voice_cli_supports_dry_run_and_once_mode():
    parser = build_arg_parser()
    args = parser.parse_args(["--dry-run", "--once"])

    assert args.dry_run is True
    assert args.once is True
