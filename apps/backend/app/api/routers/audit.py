"""監査ログ API ルーター."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.adapters.sql.session import get_session
from app.api.schemas.audit import AuthAuditLogItemResponse, AuthAuditLogListResponse
from app.core.security.session import require_session_user
from app.models.audit.auth_audit_log import AuthAuditEventType, AuthAuditLog
from app.repositories.audit.auth_audit_log_repository import list_auth_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])


def _to_auth_audit_log_item(
    log: AuthAuditLog,
    *,
    user_display_name: str | None,
    user_email: str | None,
) -> AuthAuditLogItemResponse:
    metadata: dict[str, object] | None = None
    if isinstance(log.audit_metadata, dict):
        metadata = log.audit_metadata
    elif isinstance(log.audit_metadata, str):
        try:
            parsed_metadata = json.loads(log.audit_metadata)
        except json.JSONDecodeError:
            parsed_metadata = None
        if isinstance(parsed_metadata, dict):
            metadata = parsed_metadata

    return AuthAuditLogItemResponse(
        id=log.id,
        occurred_at=log.occurred_at,
        event_type=AuthAuditEventType(log.event_type),
        user_id=log.user_id,
        user_display_name=user_display_name,
        user_email=user_email,
        session_id=log.session_id,
        provider=log.provider,
        client_ip=str(log.client_ip) if log.client_ip is not None else None,
        xff_raw=log.xff_raw,
        connection_ip=str(log.connection_ip) if log.connection_ip is not None else None,
        user_agent=log.user_agent,
        reason_code=log.reason_code,
        metadata=metadata,
    )


@router.get("/audit-logs", response_model=AuthAuditLogListResponse)
async def get_auth_audit_logs(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    event_type: AuthAuditEventType | None = None,
    user_id: UUID | None = None,
    session_id: UUID | None = None,
    occurred_from: datetime | None = Query(default=None, alias="from"),
    occurred_to: datetime | None = Query(default=None, alias="to"),
    session: Session = Depends(get_session),
) -> AuthAuditLogListResponse:
    """監査ログ一覧を返す（ログイン済みユーザー向け）."""
    await require_session_user(request, session)
    items, total = list_auth_audit_logs(
        session,
        page=page,
        page_size=page_size,
        event_type=event_type,
        user_id=user_id,
        session_id=session_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )
    return AuthAuditLogListResponse(
        page=page,
        page_size=page_size,
        total=total,
        items=[
            _to_auth_audit_log_item(
                log,
                user_display_name=user_display_name,
                user_email=user_email,
            )
            for log, user_display_name, user_email in items
        ],
    )
