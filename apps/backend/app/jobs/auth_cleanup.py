"""
認証系 cleanup バッチの CLI エントリポイント.

Step 7-2 では CLI の受け口のみを実装し、
削除ロジック本体は Step 7-3 / 7-4 で追加する。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import perf_counter

from app.adapters.postgres.session import get_session_factory
from app.core.logging.config import configure_logging, get_logger
from app.core.settings import get_settings
from app.repositories.auth.auth_audit_log_repository import (
    count_rows_in_audit_partition,
    drop_audit_partition,
    ensure_next_month_audit_partition,
    list_audit_partitions_for_drop,
)
from app.repositories.auth.session_repository import (
    count_expired_sessions_for_cleanup,
    delete_expired_sessions_batch,
)

logger = get_logger(__name__)


def _batch_size_type(value: str) -> int:
    parsed = int(value)
    if not 100 <= parsed <= 50000:
        raise argparse.ArgumentTypeError("--batch-size must be between 100 and 50000")
    return parsed


def _month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_months(dt: datetime, months: int) -> datetime:
    """
    月初日時に対する月単位の加減算.
    """
    absolute_month = (dt.year * 12 + (dt.month - 1)) + months
    year = absolute_month // 12
    month = (absolute_month % 12) + 1
    return dt.replace(year=year, month=month, day=1)


@dataclass(slots=True)
class CleanupResult:
    """cleanup 実行結果."""

    job_name: str
    status: str
    deleted_count: int
    duration_ms: float
    error: str | None = None


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
        type=_batch_size_type,
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
        type=_batch_size_type,
        default=None,
        help="1 回の実行で処理する最大件数（未指定時は CLEANUP_BATCH_SIZE）",
    )

    return parser


async def _run_sessions_cleanup(*, dry_run: bool, batch_size: int) -> CleanupResult:
    start = perf_counter()
    settings = get_settings()

    if not settings.session_cleanup_enabled:
        return CleanupResult(
            job_name="sessions_cleanup",
            status="disabled",
            deleted_count=0,
            duration_ms=(perf_counter() - start) * 1000,
        )

    run_at = datetime.now(timezone.utc)
    cutoff = run_at - timedelta(
        days=settings.session_expired_grace_days
    )
    session_factory = get_session_factory()
    target_count = 0

    async with session_factory() as session:
        async with session.begin():
            target_count = await count_expired_sessions_for_cleanup(
                session,
                expires_before=cutoff,
            )

    logger.info(
        "cleanup.sessions.criteria",
        run_at=run_at.isoformat(),
        delete_before_expires_at=cutoff.isoformat(),
        grace_days=settings.session_expired_grace_days,
        target_count=target_count,
        dry_run=dry_run,
        batch_size=batch_size,
    )

    if dry_run:
        return CleanupResult(
            job_name="sessions_cleanup",
            status="dry_run",
            deleted_count=target_count,
            duration_ms=(perf_counter() - start) * 1000,
        )

    deleted_total = 0
    while True:
        async with session_factory() as session:
            async with session.begin():
                deleted = await delete_expired_sessions_batch(
                    session,
                    expires_before=cutoff,
                    batch_size=batch_size,
                )
        deleted_total += deleted
        if deleted < batch_size:
            break

    logger.info(
        "cleanup.sessions.deleted",
        run_at=run_at.isoformat(),
        cutoff=cutoff.isoformat(),
        target_count=target_count,
        batch_size=batch_size,
        deleted_count=deleted_total,
    )
    return CleanupResult(
        job_name="sessions_cleanup",
        status="success",
        deleted_count=deleted_total,
        duration_ms=(perf_counter() - start) * 1000,
    )


async def _run_audit_cleanup(*, dry_run: bool, batch_size: int) -> CleanupResult:
    start = perf_counter()
    settings = get_settings()

    if not settings.audit_cleanup_enabled:
        return CleanupResult(
            job_name="audit_retention_cleanup",
            status="disabled",
            deleted_count=0,
            duration_ms=(perf_counter() - start) * 1000,
        )

    run_at = datetime.now(timezone.utc)
    current_month_start = _month_start(run_at)
    keep_from_month = _add_months(
        current_month_start,
        -(settings.auth_audit_retention_months - 1),
    )
    partition_drop_before_month = keep_from_month.date()

    next_month_start = _add_months(current_month_start, 1)
    next_next_month_start = _add_months(current_month_start, 2)

    session_factory = get_session_factory()

    if dry_run:
        async with session_factory() as session:
            async with session.begin():
                drop_targets = await list_audit_partitions_for_drop(
                    session,
                    drop_before_month=partition_drop_before_month,
                )
                dropped_rows = 0
                for schema_name, table_name in drop_targets:
                    dropped_rows += await count_rows_in_audit_partition(
                        session,
                        schema_name=schema_name,
                        table_name=table_name,
                    )
        logger.info(
            "cleanup.audit.dry_run",
            run_at=run_at.isoformat(),
            current_month=current_month_start.date().isoformat(),
            keep_from_month=keep_from_month.date().isoformat(),
            drop_before_month=partition_drop_before_month.isoformat(),
            drop_partition_count=len(drop_targets),
            drop_candidate_row_count=dropped_rows,
            next_partition=f"auth_audit_logs_{next_month_start:%Y_%m}",
        )
        return CleanupResult(
            job_name="audit_retention_cleanup",
            status="dry_run",
            deleted_count=dropped_rows,
            duration_ms=(perf_counter() - start) * 1000,
        )

    dropped_row_count = 0
    dropped_partitions = 0

    async with session_factory() as session:
        async with session.begin():
            drop_targets = await list_audit_partitions_for_drop(
                session,
                drop_before_month=partition_drop_before_month,
            )
            for schema_name, table_name in drop_targets:
                dropped_row_count += await count_rows_in_audit_partition(
                    session,
                    schema_name=schema_name,
                    table_name=table_name,
                )
                await drop_audit_partition(
                    session,
                    schema_name=schema_name,
                    table_name=table_name,
                )
                dropped_partitions += 1

    async with session_factory() as session:
        async with session.begin():
            await ensure_next_month_audit_partition(
                session,
                partition_start=next_month_start,
                partition_end=next_next_month_start,
            )

    total_deleted = dropped_row_count
    logger.info(
        "cleanup.audit.retention",
        run_at=run_at.isoformat(),
        current_month=current_month_start.date().isoformat(),
        keep_from_month=keep_from_month.date().isoformat(),
        drop_before_month=partition_drop_before_month.isoformat(),
        drop_partition_count=dropped_partitions,
        dropped_partition_row_count=dropped_row_count,
        deleted_count=total_deleted,
        created_partition=f"auth_audit_logs_{next_month_start:%Y_%m}",
    )
    return CleanupResult(
        job_name="audit_retention_cleanup",
        status="success",
        deleted_count=total_deleted,
        duration_ms=(perf_counter() - start) * 1000,
    )


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    configure_logging(level=settings.api_log_level)

    batch_size = args.batch_size or settings.cleanup_batch_size
    job_name = (
        "sessions_cleanup"
        if args.command == "sessions"
        else "audit_retention_cleanup"
        if args.command == "audit"
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
            result = await _run_sessions_cleanup(
                dry_run=args.dry_run,
                batch_size=batch_size,
            )
        elif args.command == "audit":
            result = await _run_audit_cleanup(
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


if __name__ == "__main__":
    sys.exit(main())
