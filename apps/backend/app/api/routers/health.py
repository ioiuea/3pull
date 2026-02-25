"""
ヘルスチェック API のルーター定義.

- `/health` エンドポイントを公開する
- レスポンスは `schemas.health.HealthResponse` で型定義する
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.network.tcp import tcp_ping
from app.adapters.postgres.session import get_session
from app.api.schemas.health import (
    HealthDependencies,
    HealthResponse,
    TcpDependencyHealth,
)
from app.core.settings import get_settings
from app.services.auth.session_auth_service import (
    SessionAuthError,
    resolve_user_by_session_token,
)
from app.services.health import _host_port_from_url

router = APIRouter(tags=["health"])


async def _require_authenticated_session(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    ヘルスチェック API 用の認証依存.

    セッション Cookie からログインユーザーを解決できない場合は 401 を返す。
    """
    cookie_name = get_settings().session_cookie_name
    raw_token = request.cookies.get(cookie_name)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "session_missing", "message": "Session cookie is missing"},
        )
    try:
        await resolve_user_by_session_token(session, raw_token=raw_token)
    except SessionAuthError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": error.code.value, "message": error.message},
        ) from error


@router.get("/health", response_model=HealthResponse)
async def get_health(
    _: None = Depends(_require_authenticated_session),
) -> HealthResponse:
    """サービスの稼働状態を返す。"""
    settings = get_settings()

    if not settings.database_url:
        postgres_result = TcpDependencyHealth(
            host="",
            port=5432,
            ok=False,
            latency_ms=0,
            error="DATABASE_URL is not set",
        )
        return HealthResponse(
            status="degraded",
            dependencies=HealthDependencies(postgres=postgres_result),
        )

    postgres_target = _host_port_from_url(settings.database_url)
    if postgres_target is None:
        postgres_result = TcpDependencyHealth(
            host="",
            port=5432,
            ok=False,
            latency_ms=0,
            error="DATABASE_URL is invalid",
        )
        return HealthResponse(
            status="degraded",
            dependencies=HealthDependencies(postgres=postgres_result),
        )
    host, port = postgres_target

    ok, latency_ms, error = await run_in_threadpool(tcp_ping, host, port)
    postgres_result = TcpDependencyHealth(
        host=host,
        port=port,
        ok=ok,
        latency_ms=latency_ms,
        error=error,
    )
    return HealthResponse(
        status="ok" if ok else "degraded",
        dependencies=HealthDependencies(postgres=postgres_result),
    )
