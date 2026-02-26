"""
認証監査ログサービス.

- 認証系ユースケースから監査ログ作成を呼び出す窓口
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth.auth_audit_log import AuthAuditEventType, AuthAuditLog
from app.repositories.auth.auth_audit_log_repository import create_auth_audit_log

ALLOWED_METADATA_KEYS = {
    "path",
    "method",
    "request_id",
    "user_type",
    "reason_detail",
    "lockout_count",
    "lockout_until",
    "entra_tenant_id",
    "entra_oid",
    "mfa_performed",
    "metadata_truncated",
}
MAX_METADATA_BYTES = 4096


@dataclass(slots=True)
class AuthAuditLogPayload:
    """
    監査ログ作成ペイロード.

    Attributes:
        event_type: 監査イベント種別（ENUM）
        user_id: ユーザー ID
        session_id: セッション ID
        provider: 認証プロバイダー（entra/email）
        client_ip: 実クライアント IP
        xff_raw: X-Forwarded-For 生値
        connection_ip: 直近接続元 IP
        user_agent: User-Agent
        reason_code: 失敗理由コードなど
        metadata: 追加メタデータ
        occurred_at: 発生時刻（未指定時は保存時刻）
    """

    event_type: AuthAuditEventType
    user_id: UUID | None = None
    session_id: UUID | None = None
    provider: str | None = None
    client_ip: str | None = None
    xff_raw: str | None = None
    connection_ip: str | None = None
    user_agent: str | None = None
    reason_code: str | None = None
    metadata: dict[str, object] | None = None
    occurred_at: datetime | None = None


def _normalize_metadata(
    metadata: dict[str, object] | None,
) -> dict[str, object] | None:
    """
    metadata を allowlist/サイズ制約に合わせて正規化する.

    仕様:
    - allowlist 外キーは破棄する
    - JSONシリアライズ結果が 4KB を超える場合は縮退し
      `metadata_truncated=true` を付与する

    Args:
        metadata: 入力metadata

    Returns:
        dict[str, object] | None: 正規化後metadata
    """
    if not metadata:
        return None

    filtered = {k: v for k, v in metadata.items() if k in ALLOWED_METADATA_KEYS}
    if not filtered:
        return None

    encoded = json.dumps(filtered, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    if len(encoded) <= MAX_METADATA_BYTES:
        return filtered

    # 4KB超過時は値を縮退し、トランケーションフラグを強制付与する。
    truncated: dict[str, object] = {}
    for key in ALLOWED_METADATA_KEYS:
        if key == "metadata_truncated":
            continue
        if key in filtered:
            value = filtered[key]
            if isinstance(value, (str, int, float, bool)) or value is None:
                truncated[key] = value
            else:
                truncated[key] = str(value)

    truncated["metadata_truncated"] = True
    encoded_truncated = json.dumps(
        truncated, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    if len(encoded_truncated) <= MAX_METADATA_BYTES:
        return truncated

    # それでも超過する場合は最小情報のみ残す。
    return {"metadata_truncated": True}


async def record_auth_audit_log(
    session: AsyncSession,
    *,
    payload: AuthAuditLogPayload,
) -> AuthAuditLog:
    """
    認証監査ログを記録する.

    Args:
        session: DB セッション
        payload: 監査ログ作成情報

    Returns:
        AuthAuditLog: 作成済み監査ログ
    """
    normalized_metadata = _normalize_metadata(payload.metadata)
    return await create_auth_audit_log(
        session,
        event_type=payload.event_type,
        user_id=payload.user_id,
        session_id=payload.session_id,
        provider=payload.provider,
        client_ip=payload.client_ip,
        xff_raw=payload.xff_raw,
        connection_ip=payload.connection_ip,
        user_agent=payload.user_agent,
        reason_code=payload.reason_code,
        metadata=normalized_metadata,
        occurred_at=payload.occurred_at,
    )
