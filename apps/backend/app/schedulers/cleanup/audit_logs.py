from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter

from app.adapters.postgres.session import get_session_factory
from app.core.logging.config import get_logger
from app.core.settings import get_settings
from app.repositories.auth.auth_audit_log_repository import (
    count_rows_in_audit_partition,
    drop_audit_partition,
    ensure_next_month_audit_partition,
    list_audit_partitions_for_drop,
)
from app.schedulers.cleanup.common import CleanupResult, add_months, month_start

logger = get_logger(__name__)


async def run_audit_cleanup(*, dry_run: bool, batch_size: int) -> CleanupResult:
    del batch_size  # cleanup interface を揃えるために受け取るが未使用

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
    current_month_start = month_start(run_at)
    keep_from_month = add_months(
        current_month_start,
        -(settings.auth_audit_retention_months - 1),
    )
    partition_drop_before_month = keep_from_month.date()

    next_month_start = add_months(current_month_start, 1)
    next_next_month_start = add_months(current_month_start, 2)

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

    logger.info(
        "cleanup.audit.retention",
        run_at=run_at.isoformat(),
        current_month=current_month_start.date().isoformat(),
        keep_from_month=keep_from_month.date().isoformat(),
        drop_before_month=partition_drop_before_month.isoformat(),
        drop_partition_count=dropped_partitions,
        dropped_partition_row_count=dropped_row_count,
        deleted_count=dropped_row_count,
        created_partition=f"auth_audit_logs_{next_month_start:%Y_%m}",
    )
    return CleanupResult(
        job_name="audit_retention_cleanup",
        status="success",
        deleted_count=dropped_row_count,
        duration_ms=(perf_counter() - start) * 1000,
    )
