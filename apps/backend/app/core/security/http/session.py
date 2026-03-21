"""FastAPI 向け session ベース API protect."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.adapters.sql.session import get_session
from app.core.settings import get_settings
from app.models.auth.user import User
from app.services.auth.session_auth_service import (
    SessionAuthError,
    resolve_user_by_session_token,
)

SESSION_MISSING_CODE = "session_missing"
SESSION_MISSING_MESSAGE = "Session cookie is missing"


@dataclass(slots=True)
class AuthenticatedSessionContext:
    """認証済みセッションの解決結果."""

    user: User
    raw_token: str


def raise_session_missing_http_error() -> NoReturn:
    """セッション Cookie 未設定を 401 へ変換する."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": SESSION_MISSING_CODE,
            "message": SESSION_MISSING_MESSAGE,
        },
    )


def raise_session_auth_http_error(error: SessionAuthError) -> NoReturn:
    """セッション認証エラーを 401 へ変換する."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": error.code.value, "message": error.message},
    ) from error


def resolve_session_cookie_token(request: Request) -> str | None:
    """Request Cookie から生セッショントークンを取得する."""
    cookie_name = get_settings().session_cookie_name
    return request.cookies.get(cookie_name)


async def require_session_context(
    request: Request,
    session: Session = Depends(get_session),
) -> AuthenticatedSessionContext:
    """Cookie セッションから現在ユーザーと生トークンを解決する."""
    raw_token = resolve_session_cookie_token(request)
    if not raw_token:
        raise_session_missing_http_error()

    try:
        user = await resolve_user_by_session_token(session, raw_token=raw_token)
    except SessionAuthError as error:
        raise_session_auth_http_error(error)

    return AuthenticatedSessionContext(user=user, raw_token=raw_token)


async def require_current_user(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    """Cookie セッションから現在ユーザーだけを解決する."""
    context = await require_session_context(request, session)
    return context.user


async def require_authenticated_session(
    request: Request,
    session: Session = Depends(get_session),
) -> None:
    """Cookie セッションの存在と有効性のみを検証する."""
    await require_session_context(request, session)


__all__ = [
    "AuthenticatedSessionContext",
    "raise_session_auth_http_error",
    "raise_session_missing_http_error",
    "require_authenticated_session",
    "require_current_user",
    "require_session_context",
    "resolve_session_cookie_token",
]
