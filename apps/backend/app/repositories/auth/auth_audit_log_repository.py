"""
AuthAuditLog モデル向けリポジトリ.

- 監査ログの作成を扱う
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, select, text
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


async def list_audit_partitions_for_drop(
    session: AsyncSession,
    *,
    drop_before_month: date,
) -> list[tuple[str, str]]:
    """
    retention で DROP 対象となる月次パーティション一覧を返す.

    Args:
        session: DB セッション
        drop_before_month: この月初より前のパーティションを DROP 対象にする

    Returns:
        list[tuple[str, str]]: (schema_name, table_name)
    """
    stmt = text(
        """
        SELECT child_ns.nspname AS schema_name, child.relname AS table_name
        FROM pg_inherits inh
        JOIN pg_class parent ON parent.oid = inh.inhparent
        JOIN pg_namespace parent_ns ON parent_ns.oid = parent.relnamespace
        JOIN pg_class child ON child.oid = inh.inhrelid
        JOIN pg_namespace child_ns ON child_ns.oid = child.relnamespace
        WHERE parent.relname = 'auth_audit_logs'
          AND parent_ns.nspname = current_schema()
          AND child.relname ~ '^auth_audit_logs_[0-9]{4}_[0-9]{2}$'
          AND to_date(substring(child.relname from '([0-9]{4}_[0-9]{2})$'), 'YYYY_MM')
              < :drop_before_month
        ORDER BY child.relname
        """
    )
    result = await session.execute(stmt, {"drop_before_month": drop_before_month})
    return [(str(row[0]), str(row[1])) for row in result.all()]


async def count_rows_in_audit_partition(
    session: AsyncSession,
    *,
    schema_name: str,
    table_name: str,
) -> int:
    """
    指定パーティション内の件数を返す.
    """
    stmt = text(f'SELECT count(*) FROM "{schema_name}"."{table_name}"')
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def drop_audit_partition(
    session: AsyncSession,
    *,
    schema_name: str,
    table_name: str,
) -> None:
    """
    指定パーティションを DROP する.
    """
    await session.execute(text(f'DROP TABLE IF EXISTS "{schema_name}"."{table_name}"'))


async def delete_audit_logs_before_cutoff_in_boundary_month(
    session: AsyncSession,
    *,
    boundary_month_start: datetime,
    cutoff: datetime,
    batch_size: int,
) -> int:
    """
    境界月に残る保持期限超過データをバッチ削除する.
    """
    stmt = text(
        """
        WITH targets AS (
            SELECT id, occurred_at
            FROM auth_audit_logs
            WHERE occurred_at >= :boundary_month_start
              AND occurred_at < :cutoff
            ORDER BY occurred_at ASC, id ASC
            LIMIT :batch_size
        ),
        deleted AS (
            DELETE FROM auth_audit_logs AS logs
            USING targets
            WHERE logs.id = targets.id
              AND logs.occurred_at = targets.occurred_at
            RETURNING 1
        )
        SELECT count(*) FROM deleted
        """
    )
    result = await session.execute(
        stmt,
        {
            "boundary_month_start": boundary_month_start,
            "cutoff": cutoff,
            "batch_size": batch_size,
        },
    )
    return int(result.scalar_one())


async def count_audit_logs_before_cutoff_in_boundary_month(
    session: AsyncSession,
    *,
    boundary_month_start: datetime,
    cutoff: datetime,
) -> int:
    """
    境界月で保持期限超過となる件数を返す.
    """
    stmt = text(
        """
        SELECT count(*)
        FROM auth_audit_logs
        WHERE occurred_at >= :boundary_month_start
          AND occurred_at < :cutoff
        """
    )
    result = await session.execute(
        stmt,
        {
            "boundary_month_start": boundary_month_start,
            "cutoff": cutoff,
        },
    )
    return int(result.scalar_one())


async def ensure_next_month_audit_partition(
    session: AsyncSession,
    *,
    partition_start: datetime,
    partition_end: datetime,
) -> None:
    """
    翌月分パーティションを作成する（存在時は何もしない）。
    """
    table_name = f"auth_audit_logs_{partition_start:%Y_%m}"
    stmt = text(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name}
        PARTITION OF auth_audit_logs
        FOR VALUES FROM (:partition_start) TO (:partition_end)
        """
    )
    await session.execute(
        stmt,
        {
            "partition_start": partition_start,
            "partition_end": partition_end,
        },
    )
