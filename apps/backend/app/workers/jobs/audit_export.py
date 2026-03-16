"""監査ログエクスポートの Queue 非依存ハンドラ."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from io import StringIO
from typing import cast
from uuid import UUID
from zoneinfo import ZoneInfo

from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
from sqlalchemy import String, and_, func, or_, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value
from sqlalchemy.sql.elements import ColumnElement

from app.adapters.sql.session import get_session_factory
from app.adapters.storage import upload_bytes
from app.core.settings import get_settings
from app.models.audit.auth_audit_log import AuthAuditEventType, AuthAuditLog
from app.models.auth.user import User
from app.models.jobs.async_job import AsyncJobStatus, AsyncJobType
from app.models.jobs.async_job_artifact import AsyncJobArtifactType
from app.repositories.jobs.async_job_artifact_repository import (
    create_async_job_artifact,
)
from app.repositories.jobs.async_job_repository import (
    claim_queued_job_for_run,
    get_async_job_by_id,
    update_async_job_status,
)

_ALLOWED_EXPORT_TIMEZONES = {"UTC", "Asia/Tokyo"}
_EXPORT_CHUNK_SIZE = 1000


class PermanentExportError(RuntimeError):
    """再試行しても解消しないエラー."""


class RetryableExportError(RuntimeError):
    """再試行で解消する可能性がある一時エラー."""


class JobCanceledExportError(RuntimeError):
    """ジョブがキャンセル済みであることを表すエラー."""


def _hydrate_audit_metadata(log: AuthAuditLog) -> None:
    if not isinstance(log.audit_metadata, str):
        return
    try:
        metadata = json.loads(log.audit_metadata)
    except json.JSONDecodeError:
        return
    set_committed_value(log, "audit_metadata", metadata)


def _build_filters(
    *,
    event_type: AuthAuditEventType | None,
    provider: str | None,
    keyword: str | None,
    occurred_from: datetime | None,
    occurred_to: datetime | None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []
    if event_type is not None:
        filters.append(AuthAuditLog.event_type == event_type)
    if provider:
        filters.append(AuthAuditLog.provider == provider)
    if occurred_from is not None:
        filters.append(AuthAuditLog.occurred_at >= occurred_from)
    if occurred_to is not None:
        filters.append(AuthAuditLog.occurred_at <= occurred_to)
    if keyword:
        escaped = keyword.strip()
        if escaped:
            like = f"%{escaped}%"
            filters.append(
                or_(
                    User.email.ilike(like),
                    User.display_name.ilike(like),
                    AuthAuditLog.reason_code.ilike(like),
                    AuthAuditLog.user_agent.ilike(like),
                    sql_cast(AuthAuditLog.event_type, String).ilike(like),
                    sql_cast(AuthAuditLog.audit_metadata, String).ilike(like),
                )
            )
    return filters


def count_auth_audit_logs_for_export_job(
    session: Session,
    *,
    event_type: AuthAuditEventType | None = None,
    provider: str | None = None,
    keyword: str | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> int:
    filters = _build_filters(
        event_type=event_type,
        provider=provider,
        keyword=keyword,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )
    stmt = (
        select(func.count(AuthAuditLog.id))
        .select_from(AuthAuditLog)
        .outerjoin(User, AuthAuditLog.user_id == User.id)
    )
    if filters:
        stmt = stmt.where(and_(*filters))
    return int(session.execute(stmt).scalar_one())


def list_auth_audit_logs_for_export_job(
    session: Session,
    *,
    limit: int,
    offset: int,
    event_type: AuthAuditEventType | None = None,
    provider: str | None = None,
    keyword: str | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> list[tuple[AuthAuditLog, str | None, str | None]]:
    filters = _build_filters(
        event_type=event_type,
        provider=provider,
        keyword=keyword,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )
    stmt = (
        select(AuthAuditLog, User.display_name, User.email)
        .select_from(AuthAuditLog)
        .outerjoin(User, AuthAuditLog.user_id == User.id)
    )
    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = (
        stmt.order_by(AuthAuditLog.occurred_at.desc(), AuthAuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = session.execute(stmt).all()
    items = [(row[0], row[1], row[2]) for row in rows]
    for log, _, _ in items:
        _hydrate_audit_metadata(log)
    return items


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
        metadata = log.audit_metadata
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                pass
        writer.writerow(
            [
                str(log.id),
                occurred_at,
                str(log.event_type),
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
                json.dumps(metadata, ensure_ascii=False)
                if metadata is not None
                else "",
            ]
        )
        row_count += 1

    return output.getvalue().encode("utf-8-sig"), row_count


async def mark_auth_audit_export_failed(*, job_id: str, error_message: str) -> None:
    parsed_job_id = UUID(job_id)
    session_factory = get_session_factory()
    with session_factory.begin() as session:
        job = get_async_job_by_id(session, job_id=parsed_job_id)
        if job is None:
            return
        update_async_job_status(
            session,
            job=job,
            status=AsyncJobStatus.FAILED,
            finished_at=datetime.now(timezone.utc),
            error_message=error_message[:2048],
        )


async def execute_auth_audit_export_job(*, job_id: str) -> tuple[str, int, int]:
    settings = get_settings()
    parsed_job_id = UUID(job_id)
    session_factory = get_session_factory()

    with session_factory.begin() as session:
        job = get_async_job_by_id(session, job_id=parsed_job_id)
        if job is None:
            raise RetryableExportError("Export job not found yet")
        if job.job_type != AsyncJobType.AUTH_AUDIT_EXPORT:
            raise PermanentExportError("Invalid job type for audit export task")
        if job.status == AsyncJobStatus.CANCELED:
            raise JobCanceledExportError("Export job was canceled before start")
        if job.status in {
            AsyncJobStatus.SUCCEEDED,
            AsyncJobStatus.FAILED,
            AsyncJobStatus.EXPIRED,
        }:
            raise JobCanceledExportError("Export job is already finalized")
        if job.status == AsyncJobStatus.RUNNING:
            raise RetryableExportError("Export job is already running")

        started_at = datetime.now(timezone.utc)
        claimed_job = claim_queued_job_for_run(
            session,
            job_id=parsed_job_id,
            started_at=started_at,
        )
        if claimed_job is None:
            current = get_async_job_by_id(session, job_id=parsed_job_id)
            if current is None:
                raise RetryableExportError("Export job not found during claim")
            if current.status == AsyncJobStatus.CANCELED:
                raise JobCanceledExportError("Export job was canceled before start")
            if current.status in {
                AsyncJobStatus.SUCCEEDED,
                AsyncJobStatus.FAILED,
                AsyncJobStatus.EXPIRED,
            }:
                raise JobCanceledExportError("Export job is already finalized")
            raise RetryableExportError("Export job could not be claimed for run")

        requested_payload = (
            claimed_job.requested_payload
            if isinstance(claimed_job.requested_payload, dict)
            else {}
        )
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
    with session_factory.begin() as session:
        total_count = count_auth_audit_logs_for_export_job(
            session,
            event_type=event_type,
            provider=provider,
            keyword=keyword,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        )

    if total_count > settings.async_job_max_rows_per_job:
        raise PermanentExportError(
            "Export row limit exceeded "
            f"({total_count} > {settings.async_job_max_rows_per_job})"
        )

    offset = 0
    rows: list[tuple[AuthAuditLog, str | None, str | None]] = []
    while offset < total_count:
        with session_factory.begin() as session:
            current = get_async_job_by_id(session, job_id=parsed_job_id)
            if current is None:
                raise PermanentExportError("Export job not found during processing")
            if current.status == AsyncJobStatus.CANCELED:
                raise JobCanceledExportError("Export job was canceled")
            chunk = list_auth_audit_logs_for_export_job(
                session,
                limit=min(_EXPORT_CHUNK_SIZE, settings.async_job_max_rows_per_job),
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
    try:
        file_size_bytes = upload_bytes(blob_path=blob_path, data=csv_bytes)
    except (RuntimeError, ValueError) as exc:
        raise PermanentExportError(str(exc)) from exc
    except (ClientAuthenticationError, HttpResponseError) as exc:
        raise PermanentExportError(str(exc)) from exc

    with session_factory.begin() as session:
        job = get_async_job_by_id(session, job_id=parsed_job_id)
        if job is None:
            raise PermanentExportError("Export job not found after upload")
        if job.status == AsyncJobStatus.CANCELED:
            raise JobCanceledExportError("Export job was canceled before finalize")
        create_async_job_artifact(
            session,
            job_id=job.id,
            artifact_type=AsyncJobArtifactType.AUTH_AUDIT_EXPORT_FILE,
            container_name=settings.azure_blob_container,
            blob_path=blob_path,
            content_type="text/csv; charset=utf-8",
            file_size_bytes=file_size_bytes,
            expires_at=job.expires_at,
        )
        update_async_job_status(
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
