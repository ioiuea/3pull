"""
監査ログエクスポート Celery タスク.
"""

from __future__ import annotations

import asyncio
import csv
import json
from datetime import datetime, timezone
from io import StringIO
from typing import cast
from uuid import UUID
from zoneinfo import ZoneInfo

from app.adapters.postgres.session import get_session_factory
from app.adapters.queue import get_celery_app
from app.adapters.storage import upload_bytes
from app.core.logging.config import configure_logging, get_logger
from app.core.settings import get_settings
from app.models.auth.auth_audit_log import AuthAuditEventType, AuthAuditLog
from app.models.jobs.async_job import AsyncJobStatus, AsyncJobType
from app.models.jobs.async_job_artifact import AsyncJobArtifactType
from app.repositories.jobs.async_job_artifact_repository import (
    create_async_job_artifact,
)
from app.repositories.jobs.async_job_repository import (
    get_async_job_by_id,
    update_async_job_status,
)
from app.services.jobs.query import (
    count_auth_audit_logs_for_export_job,
    list_auth_audit_logs_for_export_job,
)

logger = get_logger(__name__)
celery_app = get_celery_app()

_ALLOWED_EXPORT_TIMEZONES = {"UTC", "Asia/Tokyo"}
_EXPORT_CHUNK_SIZE = 1000


class PermanentExportError(RuntimeError):
    """再試行しても解消しないエラー."""


class RetryableExportError(RuntimeError):
    """再試行で解消する可能性がある一時エラー."""


def _parse_datetime_value(raw: object) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, str):
        normalized = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    raise PermanentExportError("Invalid datetime filter format")


def _extract_filters(
    requested_filters: dict[str, object],
) -> tuple[
    AuthAuditEventType | None,
    str | None,
    str | None,
    datetime | None,
    datetime | None,
]:
    event_type_raw = requested_filters.get("event_type")
    event_type: AuthAuditEventType | None = None
    if event_type_raw is not None:
        if not isinstance(event_type_raw, str):
            raise PermanentExportError("event_type must be a string")
        try:
            event_type = AuthAuditEventType(event_type_raw)
        except ValueError as exc:
            raise PermanentExportError("Invalid event_type filter") from exc

    provider_raw = requested_filters.get("provider")
    provider = provider_raw.strip() if isinstance(provider_raw, str) else None
    keyword_raw = requested_filters.get("keyword")
    keyword = keyword_raw.strip() if isinstance(keyword_raw, str) else None

    occurred_from = _parse_datetime_value(
        requested_filters.get("date_from")
        or requested_filters.get("occurred_from")
        or requested_filters.get("from")
    )
    occurred_to = _parse_datetime_value(
        requested_filters.get("date_to")
        or requested_filters.get("occurred_to")
        or requested_filters.get("to")
    )
    return event_type, provider, keyword, occurred_from, occurred_to


def _resolve_timezone(timezone_name: str) -> ZoneInfo:
    if timezone_name not in _ALLOWED_EXPORT_TIMEZONES:
        raise PermanentExportError(
            f"timezone must be one of: {', '.join(sorted(_ALLOWED_EXPORT_TIMEZONES))}"
        )
    return ZoneInfo(timezone_name)


def _build_blob_path(*, now_utc: datetime, job_id: str) -> str:
    return f"audit-exports/{now_utc:%Y}/{now_utc:%m}/{job_id}.csv"


def _build_csv_bytes(
    *,
    rows: list[tuple[AuthAuditLog, str | None, str | None]],
    timezone_name: str,
) -> tuple[bytes, int]:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "occurred_at",
            "event_type",
            "user_id",
            "user_display_name",
            "user_email",
            "session_id",
            "provider",
            "client_ip",
            "xff_raw",
            "connection_ip",
            "user_agent",
            "reason_code",
            "metadata",
        ]
    )

    zone = _resolve_timezone(timezone_name)
    row_count = 0

    for log, user_display_name, user_email in rows:
        occurred_at = log.occurred_at.astimezone(zone).isoformat()
        writer.writerow(
            [
                str(log.id),
                occurred_at,
                log.event_type.value,
                str(log.user_id) if log.user_id else "",
                user_display_name or "",
                user_email or "",
                str(log.session_id) if log.session_id else "",
                log.provider or "",
                str(log.client_ip) if log.client_ip else "",
                log.xff_raw or "",
                str(log.connection_ip) if log.connection_ip else "",
                log.user_agent or "",
                log.reason_code or "",
                json.dumps(log.audit_metadata, ensure_ascii=False)
                if log.audit_metadata is not None
                else "",
            ]
        )
        row_count += 1

    # UTF-8 BOM
    return output.getvalue().encode("utf-8-sig"), row_count


async def _mark_failed(*, job_id: str, error_message: str) -> None:
    parsed_job_id = UUID(job_id)
    session_factory = get_session_factory()
    async with session_factory() as session:
        async with session.begin():
            job = await get_async_job_by_id(session, job_id=parsed_job_id)
            if job is None:
                return
            await update_async_job_status(
                session,
                job=job,
                status=AsyncJobStatus.FAILED,
                finished_at=datetime.now(timezone.utc),
                error_message=error_message[:2048],
            )


async def _run_export_job(*, job_id: str) -> tuple[str, int, int]:
    settings = get_settings()
    parsed_job_id = UUID(job_id)
    session_factory = get_session_factory()

    async with session_factory() as session:
        async with session.begin():
            job = await get_async_job_by_id(session, job_id=parsed_job_id)
            if job is None:
                # enqueue 直後は API 側トランザクション未コミットの可能性があるため
                # retryable として扱う。
                raise RetryableExportError("Export job not found yet")
            if job.job_type != AsyncJobType.AUTH_AUDIT_EXPORT:
                raise PermanentExportError("Invalid job type for audit export task")

            if job.status in {
                AsyncJobStatus.SUCCEEDED,
                AsyncJobStatus.EXPIRED,
                AsyncJobStatus.CANCELED,
            }:
                raise PermanentExportError("Export job is already finalized")

            await update_async_job_status(
                session,
                job=job,
                status=AsyncJobStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
            )
            requested_payload: dict[str, object] = dict(job.requested_payload)
            requested_filters_raw = requested_payload.get("requested_filters")
            requested_filters: dict[str, object]
            if isinstance(requested_filters_raw, dict):
                requested_filters = cast(dict[str, object], requested_filters_raw)
            else:
                requested_filters = {}
            timezone_name = (
                str(requested_payload.get("timezone", "UTC"))
                if requested_payload.get("timezone") is not None
                else "UTC"
            )

    event_type, provider, keyword, occurred_from, occurred_to = _extract_filters(
        requested_filters
    )
    total_count: int
    async with session_factory() as session:
        async with session.begin():
            total_count = await count_auth_audit_logs_for_export_job(
                session,
                event_type=event_type,
                provider=provider,
                keyword=keyword,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
            )

    if total_count > settings.celery_max_rows_per_job:
        raise PermanentExportError(
            "Export row limit exceeded "
            f"({total_count} > {settings.celery_max_rows_per_job})"
        )

    offset = 0
    rows: list[tuple[AuthAuditLog, str | None, str | None]] = []
    while offset < total_count:
        async with session_factory() as session:
            async with session.begin():
                chunk = await list_auth_audit_logs_for_export_job(
                    session,
                    limit=min(_EXPORT_CHUNK_SIZE, settings.celery_max_rows_per_job),
                    offset=offset,
                    event_type=event_type,
                    provider=provider,
                    keyword=keyword,
                    occurred_from=occurred_from,
                    occurred_to=occurred_to,
                )
        rows.extend(chunk)
        offset += len(chunk)
        if not chunk:
            break

    csv_bytes, row_count = _build_csv_bytes(rows=rows, timezone_name=timezone_name)
    now_utc = datetime.now(timezone.utc)
    blob_path = _build_blob_path(now_utc=now_utc, job_id=job_id)
    file_size_bytes = upload_bytes(blob_path=blob_path, data=csv_bytes)

    async with session_factory() as session:
        async with session.begin():
            job = await get_async_job_by_id(
                session,
                job_id=parsed_job_id,
            )
            if job is None:
                raise PermanentExportError("Export job not found after upload")
            await create_async_job_artifact(
                session,
                job_id=job.id,
                artifact_type=AsyncJobArtifactType.AUTH_AUDIT_EXPORT_FILE,
                container_name=settings.azure_blob_container,
                blob_path=blob_path,
                content_type="text/csv; charset=utf-8",
                file_size_bytes=file_size_bytes,
                expires_at=job.expires_at,
            )
            await update_async_job_status(
                session,
                job=job,
                status=AsyncJobStatus.SUCCEEDED,
                finished_at=now_utc,
                result_payload={
                    "row_count": row_count,
                    "file_size_bytes": file_size_bytes,
                    "artifact_type": AsyncJobArtifactType.AUTH_AUDIT_EXPORT_FILE.value,
                },
                error_message=None,
            )

    return blob_path, file_size_bytes, row_count


@celery_app.task(
    bind=True,
    name=get_settings().auth_audit_export_task_name,
    max_retries=3,
)
def export_auth_audit_logs(self, job_id: str) -> None:
    """
    監査ログエクスポートジョブを実行する.
    """
    settings = get_settings()
    configure_logging(level=settings.api_log_level)

    logger.info(
        "export.job.started",
        job_id=job_id,
        retry_count=self.request.retries,
    )

    try:
        blob_path, file_size_bytes, row_count = asyncio.run(
            _run_export_job(job_id=job_id)
        )
    except RetryableExportError as exc:
        if self.request.retries >= self.max_retries:
            asyncio.run(_mark_failed(job_id=job_id, error_message=str(exc)))
            logger.exception(
                "export.job.failed",
                job_id=job_id,
                retryable=False,
                error=str(exc),
            )
            return
        logger.warning(
            "export.job.retry",
            job_id=job_id,
            retry_count=self.request.retries + 1,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=min(10, 2**self.request.retries))
    except PermanentExportError as exc:
        asyncio.run(_mark_failed(job_id=job_id, error_message=str(exc)))
        logger.warning(
            "export.job.failed",
            job_id=job_id,
            retryable=False,
            error=str(exc),
        )
        return
    except Exception as exc:  # pragma: no cover
        if self.request.retries >= self.max_retries:
            asyncio.run(_mark_failed(job_id=job_id, error_message=str(exc)))
            logger.exception(
                "export.job.failed",
                job_id=job_id,
                retryable=False,
                error=str(exc),
            )
            return
        logger.warning(
            "export.job.retry",
            job_id=job_id,
            retry_count=self.request.retries + 1,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=min(60, 2**self.request.retries))

    logger.info(
        "export.job.succeeded",
        job_id=job_id,
        blob_path=blob_path,
        file_size_bytes=file_size_bytes,
        row_count=row_count,
    )
