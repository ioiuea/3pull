from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.models.auth.auth_identity import AuthProvider
from app.services.auth.auth_account_service import (
    AuthConflictCode,
    AuthConflictError,
    signup_email_user,
)


@pytest.mark.asyncio
async def test_signup_email_user_updates_unverified_identity(monkeypatch) -> None:
    user = SimpleNamespace(id="user-1")
    identity = SimpleNamespace(email_verified_at=None)
    update_password_hash_calls: list[str] = []
    update_user_profile_calls: list[tuple[str | None, str]] = []

    monkeypatch.setattr(
        "app.services.auth.auth_account_service.get_user_by_email",
        lambda session, email: user,
    )
    monkeypatch.setattr(
        "app.services.auth.auth_account_service.get_identity_by_user_and_provider",
        lambda session, user_id, provider: identity if provider is AuthProvider.EMAIL else None,
    )
    monkeypatch.setattr(
        "app.services.auth.auth_account_service.update_password_hash",
        lambda session, *, identity, password_hash: update_password_hash_calls.append(password_hash),
    )
    monkeypatch.setattr(
        "app.services.auth.auth_account_service.update_user_profile",
        lambda session, *, user, user_type, display_name, email: update_user_profile_calls.append(
            (display_name, email)
        ),
    )

    result = await signup_email_user(
        object(),
        email="USER@example.com",
        password="StrongPass1!",
        display_name="Updated Name",
    )

    assert result is user
    assert len(update_password_hash_calls) == 1
    assert update_user_profile_calls == [("Updated Name", "user@example.com")]


@pytest.mark.asyncio
async def test_signup_email_user_keeps_rejecting_verified_identity(monkeypatch) -> None:
    user = SimpleNamespace(id="user-1")
    identity = SimpleNamespace(email_verified_at=datetime.now(timezone.utc))

    monkeypatch.setattr(
        "app.services.auth.auth_account_service.get_user_by_email",
        lambda session, email: user,
    )
    monkeypatch.setattr(
        "app.services.auth.auth_account_service.get_identity_by_user_and_provider",
        lambda session, user_id, provider: identity if provider is AuthProvider.EMAIL else None,
    )

    with pytest.raises(AuthConflictError) as exc_info:
        await signup_email_user(
            object(),
            email="user@example.com",
            password="StrongPass1!",
            display_name="Updated Name",
        )

    assert exc_info.value.code is AuthConflictCode.EMAIL_ACCOUNT_ALREADY_EXISTS
