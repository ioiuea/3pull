"""
AuthAuditLog モデル向けリポジトリ.

- 監査ログの作成を扱う
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.auth_audit_log import AuthAuditEventType, AuthAuditLog
from app.models.auth.user import User


async def create_auth_audit_log(
    session: AsyncSession,
    *,
    event_type: AuthAuditEventType,
    user_id: UUID | None,
    session_id: UUID | None,
    provider: str | None,
    client_ip: str | None,
    xff_raw: str | None,
    connection_ip: str | None,
    user_agent: str | None,
    reason_code: str | None,
    metadata: dict[str, object] | None,
    occurred_at: datetime | None = None,
) -> AuthAuditLog:
    """
    監査ログを作成する.

    Args:
        session: DB セッション
        event_type: 監査イベント種別（ENUM）
        user_id: ユーザー ID
        session_id: セッション ID
        provider: 認証プロバイダー（entra/email）
        client_ip: 実クライアント IP
        xff_raw: X-Forwarded-For の生値
        connection_ip: 直近接続元 IP
        user_agent: User-Agent
        reason_code: 失敗理由コードなど
        metadata: 追加情報（JSONB）
        occurred_at: 発生時刻（未指定時は現在UTC）

    Returns:
        AuthAuditLog: 作成済み監査ログ
    """
    audit_log = AuthAuditLog(
        occurred_at=occurred_at or datetime.now(timezone.utc),
        event_type=event_type,
        user_id=user_id,
        session_id=session_id,
        provider=provider,
        client_ip=client_ip,
        xff_raw=xff_raw,
        connection_ip=connection_ip,
        user_agent=user_agent,
        reason_code=reason_code,
        audit_metadata=metadata,
    )
    session.add(audit_log)
    await session.flush()
    return audit_log


async def list_auth_audit_logs(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    event_type: AuthAuditEventType | None = None,
    user_id: UUID | None = None,
    session_id: UUID | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> tuple[list[tuple[AuthAuditLog, str | None, str | None]], int]:
    """
    監査ログ一覧をページング取得する.

    Returns:
        tuple[list[tuple[AuthAuditLog, str | None, str | None]], int]:
            (items, total_count)
    """
    filters = []
    if event_type is not None:
        filters.append(AuthAuditLog.event_type == event_type)
    if user_id is not None:
        filters.append(AuthAuditLog.user_id == user_id)
    if session_id is not None:
        filters.append(AuthAuditLog.session_id == session_id)
    if occurred_from is not None:
        filters.append(AuthAuditLog.occurred_at >= occurred_from)
    if occurred_to is not None:
        filters.append(AuthAuditLog.occurred_at <= occurred_to)

    where_clause = and_(*filters) if filters else None

    items_stmt = (
        select(AuthAuditLog, User.display_name, User.email)
        .select_from(AuthAuditLog)
        .outerjoin(User, AuthAuditLog.user_id == User.id)
    )
    if where_clause is not None:
        items_stmt = items_stmt.where(where_clause)
    items_stmt = (
        items_stmt.order_by(AuthAuditLog.occurred_at.desc(), AuthAuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(items_stmt)).all()
    items: list[tuple[AuthAuditLog, str | None, str | None]] = [
        (row[0], row[1], row[2]) for row in rows
    ]

    if where_clause is not None:
        count_stmt = select(func.count(AuthAuditLog.id)).where(where_clause)
    else:
        count_stmt = select(func.count(AuthAuditLog.id))
    total_count = (await session.execute(count_stmt)).scalar_one()

    return items, int(total_count)
