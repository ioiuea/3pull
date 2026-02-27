from __future__ import annotations

from datetime import datetime, timedelta, timezone
from time import perf_counter

from app.adapters.postgres.session import get_session_factory
from app.core.logging.config import get_logger
from app.core.settings import get_settings
from app.repositories.auth.session_repository import (
    count_expired_sessions_for_cleanup,
    delete_expired_sessions_batch,
)
from app.schedulers.cleanup.common import CleanupResult

logger = get_logger(__name__)


async def run_sessions_cleanup(*, dry_run: bool, batch_size: int) -> CleanupResult:
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
    cutoff = run_at - timedelta(days=settings.session_expired_grace_days)
    session_factory = get_session_factory()

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
