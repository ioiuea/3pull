"""
AuthAuditLog モデル向けリポジトリ.

- 監査ログの作成と参照を扱う
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, delete, func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.models.audit.auth_audit_log import AuthAuditEventType, AuthAuditLog
from app.models.auth.user import User


def _hydrate_audit_metadata(log: AuthAuditLog) -> None:
    if not isinstance(log.audit_metadata, str):
        return
    try:
        metadata = json.loads(log.audit_metadata)
    except json.JSONDecodeError:
        return
    set_committed_value(log, "audit_metadata", metadata)


def create_auth_audit_log(
    session: Session,
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
    """監査ログを作成する."""
    serialized_metadata = (
        json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
        if metadata is not None
        else None
    )
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
        audit_metadata=serialized_metadata,
    )
    session.add(audit_log)
    session.flush()
    return audit_log


def list_auth_audit_logs(
    session: Session,
    *,
    page: int,
    page_size: int,
    event_type: AuthAuditEventType | None = None,
    user_id: UUID | None = None,
    session_id: UUID | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> tuple[list[tuple[AuthAuditLog, str | None, str | None]], int]:
    """監査ログ一覧をページング取得する."""
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
    rows = session.execute(items_stmt).all()
    items: list[tuple[AuthAuditLog, str | None, str | None]] = [
        (row[0], row[1], row[2]) for row in rows
    ]
    for log, _, _ in items:
        _hydrate_audit_metadata(log)

    if where_clause is not None:
        count_stmt = select(func.count(AuthAuditLog.id)).where(where_clause)
    else:
        count_stmt = select(func.count(AuthAuditLog.id))
    total_count = session.execute(count_stmt).scalar_one()

    return items, int(total_count)


def count_auth_audit_logs_before_cutoff(
    session: Session,
    *,
    cutoff: datetime,
) -> int:
    stmt = select(func.count(AuthAuditLog.id)).where(AuthAuditLog.occurred_at < cutoff)
    return int(session.execute(stmt).scalar_one())


def delete_auth_audit_logs_before_cutoff_batch(
    session: Session,
    *,
    cutoff: datetime,
    batch_size: int,
) -> int:
    target_ids = list(
        session.scalars(
            select(AuthAuditLog.id)
            .where(AuthAuditLog.occurred_at < cutoff)
            .order_by(AuthAuditLog.occurred_at.asc(), AuthAuditLog.id.asc())
            .limit(batch_size)
        ).all()
    )
    if not target_ids:
        return 0

    session.execute(delete(AuthAuditLog).where(AuthAuditLog.id.in_(target_ids)))
    return len(target_ids)
