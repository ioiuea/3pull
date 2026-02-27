from app.schedulers.scheduler_cleanup import _build_parser


def test_jobs_cleanup_command_is_available() -> None:
    # 目的: cleanup CLI に jobs サブコマンドが公開されていることを保証する。
    # 条件: jobs --dry-run --batch-size を parser に渡す。
    # 期待値: command/dry_run/batch_size が期待通り解釈される。
    parser = _build_parser()

    args = parser.parse_args(["jobs", "--dry-run", "--batch-size", "1000"])

    assert args.command == "jobs"
    assert args.dry_run is True
    assert args.batch_size == 1000
