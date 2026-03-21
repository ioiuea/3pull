from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.security.http import (
    require_authenticated_session,
    require_current_user,
    require_session_context,
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
    # 条件: settings と user 解決関数をテスト用実装へ差し替え、cookie 付き request を渡す。
    # 期待値: user と raw_token を持つ context が返る。
    settings = type("Settings", (), {"session_cookie_name": "session"})()
    user = object()

    async def fake_resolve_user_by_session_token(session, *, raw_token: str):
        assert raw_token == "token-1"
        return user

    # cookie 名解決だけを安定化したいため、
    # settings は session_cookie_name だけを持つテスト用オブジェクトへ差し替える。
    monkeypatch.setattr(
        "app.core.security.http.session.get_settings",
        lambda: settings,
    )
    # DB や本物の認証サービスを呼ばず、
    # raw token から user を返す分岐だけを検証するため fake resolver を使う。
    monkeypatch.setattr(
        "app.core.security.http.session.resolve_user_by_session_token",
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
    # 条件: cookie 名だけを持つ settings に差し替え、cookie なし request を渡す。
    # 期待値: session_missing コードの 401 が送出される。
    settings = type("Settings", (), {"session_cookie_name": "session"})()
    # cookie 名解決を固定し、
    # 他の設定に依存せず missing-cookie 分岐だけを検証する。
    monkeypatch.setattr(
        "app.core.security.http.session.get_settings",
        lambda: settings,
    )

    with pytest.raises(HTTPException) as exc_info:
        await require_current_user(_build_request(), session=object())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "session_missing"


@pytest.mark.asyncio
async def test_require_session_user_raises_when_session_invalid(monkeypatch) -> None:
    # 目的: ドメインエラーが API 用の 401 に変換されることを保証する。
    # 条件: user 解決関数が SessionAuthError を送出するよう差し替える。
    # 期待値: session_invalid コードの 401 が送出される。
    settings = type("Settings", (), {"session_cookie_name": "session"})()

    async def fake_resolve_user_by_session_token(session, *, raw_token: str):
        raise SessionAuthError(
            code=SessionAuthErrorCode.SESSION_INVALID,
            message="Session is invalid",
        )

    # cookie 名解決を固定し、
    # request 解析以外の外部条件を排除するため settings を差し替える。
    monkeypatch.setattr(
        "app.core.security.http.session.get_settings",
        lambda: settings,
    )
    # 本物の session 解決処理ではなく、
    # API エラー変換の分岐だけを検証するため fake resolver を使う。
    monkeypatch.setattr(
        "app.core.security.http.session.resolve_user_by_session_token",
        fake_resolve_user_by_session_token,
    )

    with pytest.raises(HTTPException) as exc_info:
        await require_current_user(
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
    # 条件: user 解決関数が成功するよう差し替えたうえで valid cookie を渡す。
    # 期待値: 例外を送出せず関数が完了する。
    settings = type("Settings", (), {"session_cookie_name": "session"})()

    async def fake_resolve_user_by_session_token(session, *, raw_token: str):
        return object()

    # cookie 名解決を固定し、
    # guard の成功経路だけを見られるよう settings を差し替える。
    monkeypatch.setattr(
        "app.core.security.http.session.get_settings",
        lambda: settings,
    )
    # DB アクセスを避け、
    # valid session 時の成功パスだけを検証するため resolver を fake 化する。
    monkeypatch.setattr(
        "app.core.security.http.session.resolve_user_by_session_token",
        fake_resolve_user_by_session_token,
    )

    await require_authenticated_session(
        _build_request(raw_token="token-1"),
        session=object(),
    )
