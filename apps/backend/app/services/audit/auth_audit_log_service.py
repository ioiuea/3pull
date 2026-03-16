"""
認証監査ログサービス.

- 認証系ユースケースから監査ログ作成を呼び出す窓口
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit.auth_audit_log import AuthAuditEventType, AuthAuditLog
from app.repositories.audit.auth_audit_log_repository import create_auth_audit_log

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
    """監査ログ作成ペイロード."""

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
    if not metadata:
        return None

    filtered = {k: v for k, v in metadata.items() if k in ALLOWED_METADATA_KEYS}
    if not filtered:
        return None

    encoded = str(filtered).encode("utf-8")
    if len(encoded) <= MAX_METADATA_BYTES:
        return filtered

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
    if len(str(truncated).encode("utf-8")) <= MAX_METADATA_BYTES:
        return truncated

    return {"metadata_truncated": True}


async def record_auth_audit_log(
    session: Session,
    *,
    payload: AuthAuditLogPayload,
) -> AuthAuditLog:
    """認証監査ログを記録する."""
    normalized_metadata = _normalize_metadata(payload.metadata)
    return create_auth_audit_log(
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
