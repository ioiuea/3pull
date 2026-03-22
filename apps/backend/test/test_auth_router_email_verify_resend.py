from __future__ import annotations

import pytest
from starlette.requests import Request

from app.api.routers.auth import post_email_verify_resend
from app.api.schemas.auth import EmailVerifyResendRequest
from app.services.auth.auth_account_service import AuthConflictCode, AuthConflictError


def _build_request() -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/backend/auth/email/verify/resend",
        "raw_path": b"/backend/auth/email/verify/resend",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


async def _noop_record_auth_audit(*args, **kwargs) -> None:
    return None


async def _noop_record_rate_limit_failure(*args, **kwargs) -> None:
    return None


@pytest.mark.asyncio
async def test_post_email_verify_resend_returns_accepted_with_debug_token(
    monkeypatch,
) -> None:
    async def fake_issue_email_verification_token(session, *, email: str, expires_in_minutes=None):
        assert email == "user@example.com"
        return "debug-token"

    settings = type("Settings", (), {"auth_debug_return_tokens": True})()
    monkeypatch.setattr(
        "app.api.routers.auth.issue_email_verification_token",
        fake_issue_email_verification_token,
    )
    monkeypatch.setattr("app.api.routers.auth._record_auth_audit", _noop_record_auth_audit)
    monkeypatch.setattr(
        "app.api.routers.auth._record_rate_limit_failure",
        _noop_record_rate_limit_failure,
    )
    monkeypatch.setattr("app.api.routers.auth.get_settings", lambda: settings)

    result = await post_email_verify_resend(
        EmailVerifyResendRequest(email="user@example.com"),
        _build_request(),
        None,
        session=object(),
    )

    assert result.status == "accepted"
    assert result.debug_verification_token == "debug-token"


@pytest.mark.asyncio
async def test_post_email_verify_resend_masks_missing_identity(monkeypatch) -> None:
    async def fake_issue_email_verification_token(session, *, email: str, expires_in_minutes=None):
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Email identity is not found",
        )

    settings = type("Settings", (), {"auth_debug_return_tokens": False})()
    monkeypatch.setattr(
        "app.api.routers.auth.issue_email_verification_token",
        fake_issue_email_verification_token,
    )
    monkeypatch.setattr("app.api.routers.auth._record_auth_audit", _noop_record_auth_audit)
    monkeypatch.setattr(
        "app.api.routers.auth._record_rate_limit_failure",
        _noop_record_rate_limit_failure,
    )
    monkeypatch.setattr("app.api.routers.auth.get_settings", lambda: settings)

    result = await post_email_verify_resend(
        EmailVerifyResendRequest(email="missing@example.com"),
        _build_request(),
        None,
        session=object(),
    )

    assert result.status == "accepted"
    assert result.debug_verification_token is None
