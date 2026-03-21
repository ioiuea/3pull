"""HTTP request 向けのセキュリティコンテキスト解決."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.core.security.http.client_ip import (
    ResolvedClientIP,
    resolve_client_ips,
)


@dataclass(frozen=True, slots=True)
class RequestSecurityContext:
    """監査・rate limit で共通利用する request 由来の security 情報."""

    client_ip: str | None
    xff_raw: str | None
    connection_ip: str | None
    user_agent: str | None


def resolve_request_security_context(request: Request) -> RequestSecurityContext:
    """Request から security 関連の派生情報をまとめて解決する."""
    resolved_ips = resolve_client_ips(request)
    return RequestSecurityContext(
        client_ip=resolved_ips.client_ip,
        xff_raw=resolved_ips.xff_raw,
        connection_ip=resolved_ips.connection_ip,
        user_agent=request.headers.get("user-agent"),
    )


__all__ = [
    "RequestSecurityContext",
    "ResolvedClientIP",
    "resolve_client_ips",
    "resolve_request_security_context",
]
