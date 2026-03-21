"""FastAPI 向け session ベース API protect.

このモジュールは、cookie/session ベース認証の HTTP adapter を 1 箇所にまとめます。
認証ドメイン本体は `services/auth/session_auth_service.py` に残しつつ、
FastAPI の `Request` / `Depends(get_session)` / `HTTPException` 変換だけを担います。

提供する guard:
- `require_session_context`: user と raw token の両方が必要な場合
- `require_session_user`: user だけあればよい場合
- `require_authenticated_session`: 認証済みかだけ検証したい場合
"""

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
    """認証済みセッションの解決結果.

    router によっては user だけでなく、生の session token も後続処理で必要です。
    そのため両方を 1 つの値として返せるようにしています。
    """

    user: User
    raw_token: str


def raise_session_missing_http_error() -> NoReturn:
    """セッション Cookie 未設定を 401 へ変換する.

    未ログイン状態を API 全体で同じ code/message に揃えるための helper です。
    """
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": SESSION_MISSING_CODE,
            "message": SESSION_MISSING_MESSAGE,
        },
    )


def raise_session_auth_http_error(error: SessionAuthError) -> NoReturn:
    """セッション認証エラーを 401 へ変換する.

    無効トークン、期限切れ、関連 user 不在などのドメインエラーを
    API 用の `code/message` 形式へ写像します。
    """
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": error.code.value, "message": error.message},
    ) from error


def resolve_session_cookie_token(request: Request) -> str | None:
    """Request Cookie から生セッショントークンを取得する.

    cookie 名は settings から解決し、router 側へ設定詳細を漏らしません。
    """
    cookie_name = get_settings().session_cookie_name
    return request.cookies.get(cookie_name)


async def require_session_context(
    request: Request,
    session: Session = Depends(get_session),
) -> AuthenticatedSessionContext:
    """Cookie セッションから現在ユーザーと生トークンを解決する.

    役割は次の 3 つです。
    1. cookie から raw token を取得する
    2. auth service で user を解決する
    3. 失敗時は API 用の 401 へ変換する
    """
    raw_token = resolve_session_cookie_token(request)
    if not raw_token:
        raise_session_missing_http_error()

    try:
        # user 解決そのものは auth service の責務に留める。
        user = await resolve_user_by_session_token(session, raw_token=raw_token)
    except SessionAuthError as error:
        raise_session_auth_http_error(error)

    return AuthenticatedSessionContext(user=user, raw_token=raw_token)


async def require_session_user(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    """Cookie セッションから現在ユーザーだけを解決する.

    `me` や job 一覧のように user さえ取れれば十分な endpoint 向けです。
    """
    context = await require_session_context(request, session)
    return context.user


async def require_authenticated_session(
    request: Request,
    session: Session = Depends(get_session),
) -> None:
    """Cookie セッションの存在と有効性のみを検証する.

    endpoint 本体で user 情報を使わないが、
    未認証アクセスだけは拒否したい場合に使います。
    例: internal health check の保護。
    """
    await require_session_context(request, session)
