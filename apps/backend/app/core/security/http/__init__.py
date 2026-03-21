"""HTTP 保護用 security facade."""

from app.core.security.http.dependencies import (
    AuthenticatedRequestDep,
    AuthenticatedSessionDep,
    CurrentUserDep,
    require_authenticated_session,
    require_current_user,
    require_session_context,
)
from app.core.security.http.middleware import install_security_middleware
from app.core.security.http.rate_limit import (
    RateLimitDecision,
    RateLimitMode,
    RateLimitPolicy,
    RateLimitPolicyKey,
    RateLimitReason,
    RateLimitRedisStore,
    RateLimitService,
    RateLimitWindow,
    build_rate_limit_policies,
    require_rate_limit,
)
from app.core.security.http.request_context import (
    RequestSecurityContext,
    ResolvedClientIP,
    resolve_client_ips,
    resolve_request_security_context,
)
from app.core.security.http.session import (
    AuthenticatedSessionContext,
    raise_session_auth_http_error,
    raise_session_missing_http_error,
    resolve_session_cookie_token,
)

__all__ = [
    "AuthenticatedSessionContext",
    "AuthenticatedRequestDep",
    "AuthenticatedSessionDep",
    "CurrentUserDep",
    "RequestSecurityContext",
    "ResolvedClientIP",
    "RateLimitDecision",
    "RateLimitMode",
    "RateLimitPolicy",
    "RateLimitPolicyKey",
    "RateLimitReason",
    "RateLimitRedisStore",
    "RateLimitService",
    "RateLimitWindow",
    "build_rate_limit_policies",
    "install_security_middleware",
    "raise_session_auth_http_error",
    "raise_session_missing_http_error",
    "require_authenticated_session",
    "require_current_user",
    "require_rate_limit",
    "require_session_context",
    "resolve_client_ips",
    "resolve_request_security_context",
    "resolve_session_cookie_token",
]
