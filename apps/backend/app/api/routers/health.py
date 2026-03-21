"""
ヘルスチェック API のルーター定義.

- `/health` エンドポイントを公開する
- レスポンスは `schemas.health.HealthResponse` で型定義する
"""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from app.adapters.network.tcp import tcp_ping
from app.api.schemas.health import (
    HealthDependencies,
    HealthResponse,
    TcpDependencyHealth,
)
from app.core.security.http import AuthenticatedRequestDep
from app.core.settings import get_settings

router = APIRouter(tags=["health"])


def _host_port_from_url(
    database_url: str,
    default_port: int = 5432,
) -> tuple[str, int] | None:
    """DATABASE_URL から接続先 host/port を抽出する。"""
    try:
        parsed = make_url(database_url)
    except ArgumentError:
        return None

    host = parsed.host
    if not host:
        return None

    port = parsed.port or default_port
    if not (1 <= port <= 65_535):
        return None

    return host, port


def _host_port_from_fqdn(
    fqdn: str,
    default_port: int,
) -> tuple[str, int] | None:
    """FQDN 文字列から接続先 host/port を抽出する。"""
    host = fqdn.strip()
    if not host:
        return None
    if not (1 <= default_port <= 65_535):
        return None
    return host, default_port


def _host_port_from_http_url(
    raw_url: str,
    default_port: int = 443,
) -> tuple[str, int] | None:
    """HTTP(S) URL から接続先 host/port を抽出する。"""
    parsed = urlparse(raw_url)
    host = parsed.hostname
    if not host:
        return None

    port = parsed.port or default_port
    if not (1 <= port <= 65_535):
        return None

    return host, port


@router.get("/health", response_model=HealthResponse)
async def get_health(
    _: AuthenticatedRequestDep,
) -> HealthResponse:
    """サービスの稼働状態を返す。"""
    settings = get_settings()

    if not settings.database_url:
        sql_result = TcpDependencyHealth(
            host="",
            port=settings.database_default_port,
            ok=False,
            latency_ms=0,
            error="DATABASE_URL is not set",
        )
        redis_result = await _build_redis_health()
        service_bus_result = await _build_service_bus_health()
        storage_result = await _build_storage_health()
        return HealthResponse(
            status="degraded",
            dependencies=HealthDependencies(
                sql=sql_result,
                redis=redis_result,
                service_bus=service_bus_result,
                storage=storage_result,
            ),
        )

    sql_target = _host_port_from_url(
        settings.database_url,
        settings.database_default_port,
    )
    if sql_target is None:
        sql_result = TcpDependencyHealth(
            host="",
            port=settings.database_default_port,
            ok=False,
            latency_ms=0,
            error="DATABASE_URL is invalid",
        )
        redis_result = await _build_redis_health()
        service_bus_result = await _build_service_bus_health()
        storage_result = await _build_storage_health()
        return HealthResponse(
            status="degraded",
            dependencies=HealthDependencies(
                sql=sql_result,
                redis=redis_result,
                service_bus=service_bus_result,
                storage=storage_result,
            ),
        )
    host, port = sql_target

    ok, latency_ms, error = await run_in_threadpool(tcp_ping, host, port)
    sql_result = TcpDependencyHealth(
        host=host,
        port=port,
        ok=ok,
        latency_ms=latency_ms,
        error=error,
    )
    redis_result = await _build_redis_health()
    service_bus_result = await _build_service_bus_health()
    storage_result = await _build_storage_health()
    return HealthResponse(
        status=(
            "ok"
            if ok and redis_result.ok and service_bus_result.ok and storage_result.ok
            else "degraded"
        ),
        dependencies=HealthDependencies(
            sql=sql_result,
            redis=redis_result,
            service_bus=service_bus_result,
            storage=storage_result,
        ),
    )


async def _build_redis_health() -> TcpDependencyHealth:
    """Redis の TCP 到達性結果を HealthResponse 用に組み立てる。"""
    settings = get_settings()
    target = _host_port_from_fqdn(settings.redis_host or "", settings.redis_port)
    if target is None:
        return TcpDependencyHealth(
            host="",
            port=settings.redis_port,
            ok=False,
            latency_ms=0,
            error="REDIS_HOST is not set",
        )

    host, port = target
    ok, latency_ms, error = await run_in_threadpool(tcp_ping, host, port)
    return TcpDependencyHealth(
        host=host,
        port=port,
        ok=ok,
        latency_ms=latency_ms,
        error=error,
    )


async def _build_service_bus_health() -> TcpDependencyHealth:
    """Service Bus の TCP 到達性結果を HealthResponse 用に組み立てる。"""
    settings = get_settings()
    target = _host_port_from_fqdn(settings.service_bus_namespace_fqdn or "", 5671)
    if target is None:
        return TcpDependencyHealth(
            host="",
            port=5671,
            ok=False,
            latency_ms=0,
            error="SERVICE_BUS_NAMESPACE_FQDN is not set",
        )

    host, port = target
    ok, latency_ms, error = await run_in_threadpool(tcp_ping, host, port)
    return TcpDependencyHealth(
        host=host,
        port=port,
        ok=ok,
        latency_ms=latency_ms,
        error=error,
    )


async def _build_storage_health() -> TcpDependencyHealth:
    """Azure Blob Storage の TCP 到達性結果を HealthResponse 用に組み立てる。"""
    settings = get_settings()
    target = _host_port_from_http_url(settings.azure_blob_account_url or "", 443)
    if target is None:
        return TcpDependencyHealth(
            host="",
            port=443,
            ok=False,
            latency_ms=0,
            error="AZURE_BLOB_ACCOUNT_URL is not set",
        )

    host, port = target
    ok, latency_ms, error = await run_in_threadpool(tcp_ping, host, port)
    return TcpDependencyHealth(
        host=host,
        port=port,
        ok=ok,
        latency_ms=latency_ms,
        error=error,
    )
