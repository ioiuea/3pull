import asyncio

from app.schedulers.cleanup.runners.async_jobs import run_jobs_cleanup
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


def test_run_jobs_cleanup_returns_disabled_when_async_jobs_are_off(monkeypatch) -> None:
    # 目的: 非同期ジョブ機能が無効な場合、jobs cleanup が即座に disabled で返ることを保証する。
    # 条件: settings.async_jobs_enabled を False に差し替える。
    # 期待値: job_name が jobs_cleanup、status が disabled になる。
    settings = type("Settings", (), {"async_jobs_enabled": False})()
    monkeypatch.setattr(
        "app.schedulers.cleanup.runners.async_jobs.get_settings", lambda: settings
    )

    result = asyncio.run(run_jobs_cleanup(dry_run=False, batch_size=100))

    assert result.job_name == "jobs_cleanup"
    assert result.status == "disabled"
    assert result.deleted_count == 0


def test_run_jobs_cleanup_dry_run_counts_artifacts_and_stale_jobs(monkeypatch) -> None:
    # 目的: dry-run 時に期限切れ成果物と stale running ジョブの両方を集計することを保証する。
    # 条件: artifacts=2, stale running=3 を返すよう依存関数を差し替える。
    # 期待値: jobs_cleanup が dry_run で返り、deleted_count は合算 5 になる。
    settings = type(
        "Settings",
        (),
        {
            "async_jobs_enabled": True,
            "async_job_running_timeout_seconds": 2700,
        },
    )()

    class _NullContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FakeSessionFactory:
        def begin(self):
            return _NullContext()

    def _fake_count_expired(session, *, expires_before):
        return 2

    def _fake_count_stale(session, *, started_before):
        return 3

    monkeypatch.setattr(
        "app.schedulers.cleanup.runners.async_jobs.get_settings", lambda: settings
    )
    monkeypatch.setattr(
        "app.schedulers.cleanup.runners.async_jobs.get_session_factory",
        lambda: _FakeSessionFactory(),
    )
    monkeypatch.setattr(
        "app.schedulers.cleanup.runners.async_jobs.count_expired_async_job_artifacts",
        _fake_count_expired,
    )
    monkeypatch.setattr(
        "app.schedulers.cleanup.runners.async_jobs.count_stale_running_async_jobs",
        _fake_count_stale,
    )

    result = asyncio.run(run_jobs_cleanup(dry_run=True, batch_size=100))

    assert result.job_name == "jobs_cleanup"
    assert result.status == "dry_run"
    assert result.deleted_count == 5
