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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.adapters.postgres.session import get_session_factory
from app.adapters.storage import upload_bytes
from app.core.settings import get_settings
from app.models.auth.auth_audit_log import AuthAuditEventType, AuthAuditLog
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


def _build_filters(
    *,
    event_type: AuthAuditEventType | None,
    provider: str | None,
    keyword: str | None,
    occurred_from: datetime | None,
    occurred_to: datetime | None,
) -> list[ColumnElement[bool]]:
    # 件数取得と一覧取得で同じ絞り込み条件を使うため、WHERE 句だけ共通化する。
    # こうしておくと、事前の件数チェックと実際のエクスポート結果がずれにくい。
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
            # キーワードは user 情報と監査ログ本文の両方に対して横断検索する。
            # export 用途では「まず候補を広く拾う」方が使いやすいため、
            # OR 条件にしている。
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


async def count_auth_audit_logs_for_export_job(
    session: AsyncSession,
    *,
    event_type: AuthAuditEventType | None = None,
    provider: str | None = None,
    keyword: str | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> int:
    """エクスポート対象となる監査ログ件数を返す."""
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
        # user 情報が消えている監査ログも export 対象から落とさないため、
        # outer join を使う。
        .outerjoin(User, AuthAuditLog.user_id == User.id)
    )
    if filters:
        stmt = stmt.where(and_(*filters))
    return int((await session.execute(stmt)).scalar_one())


async def list_auth_audit_logs_for_export_job(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    event_type: AuthAuditEventType | None = None,
    provider: str | None = None,
    keyword: str | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> list[tuple[AuthAuditLog, str | None, str | None]]:
    """エクスポート対象となる監査ログを取得する."""
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
        # 監査ログだけは残っているケースを拾うため、ここも outer join を維持する。
        .outerjoin(User, AuthAuditLog.user_id == User.id)
    )
    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = (
        # 並び順を固定しておくことで、ページングしても同じ条件なら結果がぶれにくい。
        stmt.order_by(AuthAuditLog.occurred_at.desc(), AuthAuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()
    # 呼び出し側が ORM Row を意識しなくて済むよう、必要な shape に整えて返す。
    return [(row[0], row[1], row[2]) for row in rows]


def _parse_datetime_value(raw: object) -> datetime | None:
    # API から来る日時は文字列のことも datetime のこともあるため、ここで正規化する。
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
    # requested_payload から export 用の検索条件だけを抜き出し、型付きに戻す。
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
    # 出力 timezone は制限付きにして、想定外の ZoneInfo 依存を避ける。
    if timezone_name not in _ALLOWED_EXPORT_TIMEZONES:
        raise PermanentExportError(
            f"timezone must be one of: {', '.join(sorted(_ALLOWED_EXPORT_TIMEZONES))}"
        )
    return ZoneInfo(timezone_name)


def _build_blob_path(*, now_utc: datetime, job_id: str) -> str:
    # 月単位でまとまるようにしておくと、運用時に Blob 一覧を追いやすい。
    return f"audit-exports/{now_utc:%Y}/{now_utc:%m}/{job_id}.csv"


def _build_csv_bytes(
    *,
    rows: list[tuple[AuthAuditLog, str | None, str | None]],
    timezone_name: str,
) -> tuple[bytes, int]:
    # CSV 文字列生成は DB アクセスから切り離し、純粋な変換処理にしておく。
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
        # user 情報は join 結果なので欠けうる。CSV では空文字に寄せて欠損を表現する。
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

    return output.getvalue().encode("utf-8-sig"), row_count


async def mark_auth_audit_export_failed(*, job_id: str, error_message: str) -> None:
    # 恒久失敗時だけ runtime から呼ばれ、job を failed に確定させる。
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


async def execute_auth_audit_export_job(*, job_id: str) -> tuple[str, int, int]:
    settings = get_settings()
    parsed_job_id = UUID(job_id)
    session_factory = get_session_factory()

    async with session_factory() as session:
        async with session.begin():
            job = await get_async_job_by_id(session, job_id=parsed_job_id)
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
            # 実行開始の claim は 1 回だけ成功する。これで同一 job の並行処理を防ぐ。
            claimed_job = await claim_queued_job_for_run(
                session,
                job_id=parsed_job_id,
                started_at=started_at,
            )
            if claimed_job is None:
                current = await get_async_job_by_id(session, job_id=parsed_job_id)
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

            requested_payload: dict[str, object] = dict(claimed_job.requested_payload)
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
    async with session_factory() as session:
        async with session.begin():
            # 先に件数だけ確認し、上限超過なら重い export を始める前に止める。
            total_count = await count_auth_audit_logs_for_export_job(
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
        async with session_factory() as session:
            async with session.begin():
                current = await get_async_job_by_id(session, job_id=parsed_job_id)
                if current is None:
                    raise PermanentExportError("Export job not found during processing")
                if current.status == AsyncJobStatus.CANCELED:
                    raise JobCanceledExportError("Export job was canceled")
                # 大量件数でもメモリと DB 負荷を抑えるため、チャンク単位で読む。
                chunk = await list_auth_audit_logs_for_export_job(
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
        # Storage の必須設定不足は構成ミスなので恒久失敗に寄せる。
        raise PermanentExportError(str(exc)) from exc
    except (ClientAuthenticationError, HttpResponseError) as exc:
        # 認証拒否や権限不足など、Storage 側の明示的な失敗は
        # 再試行では解消しにくいため恒久失敗として扱う。
        raise PermanentExportError(str(exc)) from exc

    async with session_factory() as session:
        async with session.begin():
            job = await get_async_job_by_id(session, job_id=parsed_job_id)
            if job is None:
                raise PermanentExportError("Export job not found after upload")
            if job.status == AsyncJobStatus.CANCELED:
                raise JobCanceledExportError("Export job was canceled before finalize")
            # artifact 作成と succeeded 更新は同一トランザクションで揃えておく。
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
