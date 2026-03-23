"""cleanup CLI の起動処理と command ごとの実行定義."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter

from app.core.logging import configure_logging, get_logger
from app.core.settings import get_settings
from app.core.telemetry import configure_telemetry
from app.schedulers.cleanup.helpers import CleanupResult, batch_size_type
from app.schedulers.cleanup.runners import (
    run_audit_cleanup,
    run_jobs_cleanup,
    run_sessions_cleanup,
)

logger = get_logger(__name__)

CleanupRunnerFunc = Callable[..., Coroutine[object, object, CleanupResult]]


@dataclass(frozen=True)
class CleanupRunnerSpec:
    """cleanup command ごとの実行定義."""

    command: str
    job_name: str
    run: CleanupRunnerFunc


_RUNNERS: dict[str, CleanupRunnerSpec] = {
    "sessions-cleanup": CleanupRunnerSpec(
        command="sessions-cleanup",
        job_name="sessions_cleanup",
        run=run_sessions_cleanup,
    ),
    "audit-cleanup": CleanupRunnerSpec(
        command="audit-cleanup",
        job_name="audit_retention_cleanup",
        run=run_audit_cleanup,
    ),
    "jobs-cleanup": CleanupRunnerSpec(
        command="jobs-cleanup",
        job_name="jobs_cleanup",
        run=run_jobs_cleanup,
    ),
}


def list_cleanup_commands() -> tuple[str, ...]:
    """利用可能な cleanup command 一覧を返す."""
    return tuple(_RUNNERS.keys())


def get_cleanup_runner(command: str) -> CleanupRunnerSpec:
    """command に対応する cleanup runner を返す."""
    if command not in _RUNNERS:
        raise RuntimeError(f"Unsupported cleanup command: {command}")
    return _RUNNERS[command]


def _build_parser() -> argparse.ArgumentParser:
    # cleanup は 1 つの CLI から複数ジョブを呼び分ける。
    # subcommand ごとに dry-run と batch-size の共通引数をそろえている。
    parser = argparse.ArgumentParser(prog="python -m app.schedulers.batch_jobs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in list_cleanup_commands():
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="削除は行わず、対象件数のみ計測する",
        )
        command_parser.add_argument(
            "--batch-size",
            type=batch_size_type,
            default=None,
            help="1 回の実行で処理する最大件数（未指定時は CLEANUP_BATCH_SIZE）",
        )

    return parser


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    configure_logging(level=settings.api_log_level)

    batch_size = args.batch_size or settings.cleanup_batch_size
    try:
        spec = get_cleanup_runner(args.command)
    except RuntimeError:
        return 2

    service_name = settings.scheduler_service_name(spec.command)

    try:
        telemetry_enabled = configure_telemetry(
            service_name=service_name,
            connection_string=getattr(
                settings,
                "applicationinsights_connection_string",
                None,
            ),
        )
    except Exception as exc:  # pragma: no cover
        logger.exception(
            "telemetry.init.failed",
            service=service_name,
            error=str(exc),
        )
    else:
        if telemetry_enabled:
            logger.info("telemetry.init.completed", service=service_name)
        else:
            logger.info("telemetry.init.skipped", service=service_name)

    run_start = perf_counter()
    logger.info(
        "cleanup.started",
        service=service_name,
        job_name=spec.job_name,
        run_at=datetime.now(timezone.utc).isoformat(),
        dry_run=args.dry_run,
        batch_size=batch_size,
    )

    try:
        # command -> 実処理の対応はこのファイル内の registry に寄せる。
        result = await spec.run(
            dry_run=args.dry_run,
            batch_size=batch_size,
        )
    except Exception as exc:  # pragma: no cover
        duration_ms = (perf_counter() - run_start) * 1000
        logger.exception(
            "cleanup.failed",
            service=service_name,
            job_name=spec.job_name,
            status="error",
            error=str(exc),
            duration_ms=round(duration_ms, 2),
        )
        return 1

    logger.info(
        "cleanup.completed",
        service=service_name,
        job_name=result.job_name,
        status=result.status,
        deleted_count=result.deleted_count,
        duration_ms=round(result.duration_ms, 2),
        error=result.error,
    )
    return 0


def main() -> int:
    # CLI 入口。async cleanup を同期的に呼べるようにここで event loop を張る。
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args))
