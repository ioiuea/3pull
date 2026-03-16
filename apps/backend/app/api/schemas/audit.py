"""監査ログ API スキーマ."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.audit.auth_audit_log import AuthAuditEventType


class AuthAuditLogItemResponse(BaseModel):
    """監査ログ一覧の1行."""

    id: int
    occurred_at: datetime
    event_type: AuthAuditEventType
    user_id: UUID | None
    user_display_name: str | None
    user_email: str | None
    session_id: UUID | None
    provider: str | None
    client_ip: str | None
    xff_raw: str | None
    connection_ip: str | None
    user_agent: str | None
    reason_code: str | None
    metadata: dict[str, object] | None


class AuthAuditLogListResponse(BaseModel):
    """監査ログ一覧 API の応答."""

    page: int
    page_size: int
    total: int
    items: list[AuthAuditLogItemResponse]
