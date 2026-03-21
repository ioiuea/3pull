from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.security.session import (
    require_authenticated_session,
    require_session_context,
    require_session_user,
)
from app.services.auth.session_auth_service import (
    SessionAuthError,
    SessionAuthErrorCode,
)


def _build_request(
    *,
    cookie_name: str = "session",
    raw_token: str | None = None,
) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if raw_token is not None:
        headers.append((b"cookie", f"{cookie_name}={raw_token}".encode("utf-8")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_require_session_context_returns_user_and_token(monkeypatch) -> None:
    # 目的: session guard が user と raw token をまとめて返すことを保証する。
    settings = type("Settings", (), {"session_cookie_name": "session"})()
    user = object()

    async def fake_resolve_user_by_session_token(session, *, raw_token: str):
        assert raw_token == "token-1"
        return user

    monkeypatch.setattr(
        "app.core.security.session.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "app.core.security.session.resolve_user_by_session_token",
        fake_resolve_user_by_session_token,
    )

    context = await require_session_context(
        _build_request(raw_token="token-1"),
        session=object(),
    )

    assert context.user is user
    assert context.raw_token == "token-1"


@pytest.mark.asyncio
async def test_require_session_user_raises_when_cookie_missing(monkeypatch) -> None:
    # 目的: session cookie が無い場合に 401 を返すことを保証する。
    settings = type("Settings", (), {"session_cookie_name": "session"})()
    monkeypatch.setattr(
        "app.core.security.session.get_settings",
        lambda: settings,
    )

    with pytest.raises(HTTPException) as exc_info:
        await require_session_user(_build_request(), session=object())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "session_missing"


@pytest.mark.asyncio
async def test_require_session_user_raises_when_session_invalid(monkeypatch) -> None:
    # 目的: ドメインエラーが API 用の 401 に変換されることを保証する。
    settings = type("Settings", (), {"session_cookie_name": "session"})()

    async def fake_resolve_user_by_session_token(session, *, raw_token: str):
        raise SessionAuthError(
            code=SessionAuthErrorCode.SESSION_INVALID,
            message="Session is invalid",
        )

    monkeypatch.setattr(
        "app.core.security.session.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "app.core.security.session.resolve_user_by_session_token",
        fake_resolve_user_by_session_token,
    )

    with pytest.raises(HTTPException) as exc_info:
        await require_session_user(
            _build_request(raw_token="token-1"),
            session=object(),
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "session_invalid"


@pytest.mark.asyncio
async def test_require_authenticated_session_completes_for_valid_session(
    monkeypatch,
) -> None:
    # 目的: 認証済みセッション検証専用 guard が成功時に完了することを保証する。
    settings = type("Settings", (), {"session_cookie_name": "session"})()

    async def fake_resolve_user_by_session_token(session, *, raw_token: str):
        return object()

    monkeypatch.setattr(
        "app.core.security.session.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "app.core.security.session.resolve_user_by_session_token",
        fake_resolve_user_by_session_token,
    )

    await require_authenticated_session(
        _build_request(raw_token="token-1"),
        session=object(),
    )
