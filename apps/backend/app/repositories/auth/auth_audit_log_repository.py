"""
AuthAuditLog モデル向けリポジトリ.

- 監査ログの作成を扱う
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.auth_audit_log import AuthAuditEventType, AuthAuditLog


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
