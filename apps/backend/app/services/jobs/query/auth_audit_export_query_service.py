"""監査ログエクスポート向けクエリサービス."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.auth.auth_audit_log import AuthAuditEventType, AuthAuditLog
from app.models.auth.user import User


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
                    cast(AuthAuditLog.event_type, String).ilike(like),
                    cast(AuthAuditLog.audit_metadata, String).ilike(like),
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
        .outerjoin(User, AuthAuditLog.user_id == User.id)
    )
    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = (
        stmt.order_by(AuthAuditLog.occurred_at.desc(), AuthAuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()
    return [(row[0], row[1], row[2]) for row in rows]
