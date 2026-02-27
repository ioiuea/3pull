from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from time import perf_counter

from app.core.logging.config import configure_logging, get_logger
from app.core.settings import get_settings
from app.jobs.cleanup.async_jobs import run_jobs_cleanup
from app.jobs.cleanup.audit_logs import run_audit_cleanup
from app.jobs.cleanup.common import batch_size_type
from app.jobs.cleanup.sessions import run_sessions_cleanup

logger = get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.jobs.auth_cleanup")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sessions_parser = subparsers.add_parser("sessions")
    sessions_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="削除は行わず、対象件数のみ計測する",
    )
    sessions_parser.add_argument(
        "--batch-size",
        type=batch_size_type,
        default=None,
        help="1 回の実行で処理する最大件数（未指定時は CLEANUP_BATCH_SIZE）",
    )

    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="削除は行わず、対象件数のみ計測する",
    )
    audit_parser.add_argument(
        "--batch-size",
        type=batch_size_type,
        default=None,
        help="1 回の実行で処理する最大件数（未指定時は CLEANUP_BATCH_SIZE）",
    )

    jobs_parser = subparsers.add_parser("jobs")
    jobs_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="削除は行わず、対象件数のみ計測する",
    )
    jobs_parser.add_argument(
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
    job_name = (
        "sessions_cleanup"
        if args.command == "sessions"
        else "audit_retention_cleanup"
        if args.command == "audit"
        else "jobs_artifact_cleanup"
        if args.command == "jobs"
        else args.command
    )
    run_start = perf_counter()
    logger.info(
        "cleanup.started",
        job_name=job_name,
        run_at=datetime.now(timezone.utc).isoformat(),
        dry_run=args.dry_run,
        batch_size=batch_size,
    )

    try:
        if args.command == "sessions":
            result = await run_sessions_cleanup(
                dry_run=args.dry_run,
                batch_size=batch_size,
            )
        elif args.command == "audit":
            result = await run_audit_cleanup(
                dry_run=args.dry_run,
                batch_size=batch_size,
            )
        elif args.command == "jobs":
            result = await run_jobs_cleanup(
                dry_run=args.dry_run,
                batch_size=batch_size,
            )
        else:
            return 2
    except Exception as exc:  # pragma: no cover
        duration_ms = (perf_counter() - run_start) * 1000
        logger.exception(
            "cleanup.failed",
            job_name=job_name,
            status="error",
            error=str(exc),
            duration_ms=round(duration_ms, 2),
        )
        return 1

    logger.info(
        "cleanup.completed",
        job_name=result.job_name,
        status=result.status,
        deleted_count=result.deleted_count,
        duration_ms=round(result.duration_ms, 2),
        error=result.error,
    )
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args))
