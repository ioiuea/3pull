"""監査ログの保持期限超過データを段階削除する cleanup."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from time import perf_counter

from app.adapters.sql.session import get_session_factory
from app.core.logging.config import get_logger
from app.core.settings import get_settings
from app.repositories.audit.auth_audit_log_repository import (
    count_auth_audit_logs_before_cutoff,
    delete_auth_audit_logs_before_cutoff_batch,
)
from app.schedulers.cleanup.helpers import CleanupResult

logger = get_logger(__name__)


async def run_audit_cleanup(*, dry_run: bool, batch_size: int) -> CleanupResult:
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
    cutoff = run_at - timedelta(days=settings.auth_audit_retention_months * 31)
    session_factory = get_session_factory()

    with session_factory.begin() as session:
        target_count = count_auth_audit_logs_before_cutoff(
            session,
            cutoff=cutoff,
        )

    logger.info(
        "cleanup.audit.criteria",
        run_at=run_at.isoformat(),
        cutoff=cutoff.isoformat(),
        retention_months=settings.auth_audit_retention_months,
        target_count=target_count,
        dry_run=dry_run,
        batch_size=batch_size,
    )

    if dry_run:
        return CleanupResult(
            job_name="audit_retention_cleanup",
            status="dry_run",
            deleted_count=target_count,
            duration_ms=(perf_counter() - start) * 1000,
        )

    deleted_total = 0
    while True:
        with session_factory.begin() as session:
            deleted = delete_auth_audit_logs_before_cutoff_batch(
                session,
                cutoff=cutoff,
                batch_size=batch_size,
            )
        deleted_total += deleted
        if deleted < batch_size:
            break

    logger.info(
        "cleanup.audit.retention",
        run_at=run_at.isoformat(),
        cutoff=cutoff.isoformat(),
        target_count=target_count,
        deleted_count=deleted_total,
        batch_size=batch_size,
    )
    return CleanupResult(
        job_name="audit_retention_cleanup",
        status="success",
        deleted_count=deleted_total,
        duration_ms=(perf_counter() - start) * 1000,
    )
