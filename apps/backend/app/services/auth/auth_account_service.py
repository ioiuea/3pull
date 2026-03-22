"""
認証アカウント統合ポリシーを扱うサービス.

- Entra 優先の統合ルールを実装する
- Email signup の拒否条件を実装する
"""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.datetime import ensure_utc_datetime
from app.core.logging import get_logger
from app.core.security.crypto import hash_password, needs_rehash, verify_password
from app.core.settings import get_settings
from app.models.auth.auth_identity import AuthProvider
from app.models.auth.user import User, UserType
from app.repositories.auth.auth_identity_repository import (
    create_identity,
    delete_identity_by_id,
    get_identity_by_id,
    get_identity_by_provider_and_email,
    get_identity_by_provider_subject,
    get_identity_by_user_and_provider,
    mark_email_verified,
    record_failed_email_login,
    reset_failed_email_login_state,
    update_password_hash,
)
from app.repositories.auth.email_verification_token_repository import (
    consume_email_verification_token,
    create_email_verification_token,
    get_email_verification_token_by_hash,
    revoke_active_tokens_by_identity_id,
)
from app.repositories.auth.password_reset_token_repository import (
    consume_password_reset_token,
    create_password_reset_token,
    get_password_reset_token_by_hash,
    revoke_active_password_reset_tokens_by_identity_id,
)
from app.repositories.auth.session_repository import revoke_all_user_sessions
from app.repositories.auth.user_repository import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    normalize_email,
    update_user_profile,
)


class AuthConflictCode(StrEnum):
    EMAIL_ACCOUNT_ALREADY_EXISTS = "email_account_already_exists"
    ENTRA_ACCOUNT_ALREADY_EXISTS = "entra_account_already_exists"
    ENTRA_SUBJECT_CONFLICT = "entra_subject_conflict"
    EMAIL_NOT_VERIFIED = "email_not_verified"
    EMAIL_IDENTITY_NOT_FOUND = "email_identity_not_found"
    EMAIL_ALREADY_VERIFIED = "email_already_verified"
    EMAIL_VERIFICATION_TOKEN_INVALID = "email_verification_token_invalid"
    EMAIL_VERIFICATION_TOKEN_EXPIRED = "email_verification_token_expired"
    WEAK_PASSWORD = "weak_password"
    EMAIL_ACCOUNT_LOCKED = "email_account_locked"
    INVALID_CREDENTIALS = "invalid_credentials"
    CURRENT_PASSWORD_INVALID = "current_password_invalid"
    PASSWORD_REUSE_NOT_ALLOWED = "password_reuse_not_allowed"
    PASSWORD_RESET_TOKEN_INVALID = "password_reset_token_invalid"
    PASSWORD_RESET_TOKEN_EXPIRED = "password_reset_token_expired"


@dataclass(slots=True)
class AuthConflictError(Exception):
    code: AuthConflictCode
    message: str


logger = get_logger(__name__)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def validate_password_policy(password: str) -> None:
    if len(password) < 10:
        raise AuthConflictError(
            code=AuthConflictCode.WEAK_PASSWORD,
            message="Password must be at least 10 characters",
        )

    has_upper = bool(re.search(r"[A-Z]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_symbol = bool(re.search(r"[^A-Za-z0-9]", password))
    categories = sum((has_upper, has_lower, has_digit, has_symbol))
    if categories < 3:
        raise AuthConflictError(
            code=AuthConflictCode.WEAK_PASSWORD,
            message="Password must include at least 3 of upper/lower/digit/symbol",
        )


async def resolve_entra_login(
    session: Session,
    *,
    user_principal_name: str,
    entra_subject: str,
    display_name: str | None,
) -> User:
    normalized_email = normalize_email(user_principal_name)

    existing_entra_identity = get_identity_by_provider_subject(
        session,
        provider=AuthProvider.ENTRA,
        provider_subject=entra_subject,
    )
    if existing_entra_identity:
        user = get_user_by_id(session, existing_entra_identity.user_id)
        if user is None:
            raise AuthConflictError(
                code=AuthConflictCode.ENTRA_SUBJECT_CONFLICT,
                message="Entra identity exists but user is not found",
            )
        update_user_profile(
            session,
            user=user,
            user_type=UserType.INTERNAL,
            display_name=display_name,
            email=normalized_email,
        )
        return user

    user = get_user_by_email(session, normalized_email)
    if user is None:
        user = create_user(
            session,
            email=normalized_email,
            user_type=UserType.INTERNAL,
            display_name=display_name,
        )
        create_identity(
            session,
            user_id=user.id,
            provider=AuthProvider.ENTRA,
            provider_subject=entra_subject,
            email_normalized=normalized_email,
        )
        return user

    entra_identity_for_user = get_identity_by_user_and_provider(
        session, user.id, AuthProvider.ENTRA
    )
    if (
        entra_identity_for_user
        and entra_identity_for_user.provider_subject != entra_subject
    ):
        raise AuthConflictError(
            code=AuthConflictCode.ENTRA_SUBJECT_CONFLICT,
            message="Email is already linked to another Entra subject",
        )
    if entra_identity_for_user:
        update_user_profile(
            session,
            user=user,
            user_type=UserType.INTERNAL,
            display_name=display_name,
            email=normalized_email,
        )
        return user

    email_identity = get_identity_by_user_and_provider(
        session, user.id, AuthProvider.EMAIL
    )
    if email_identity:
        delete_identity_by_id(session, email_identity.id)

    create_identity(
        session,
        user_id=user.id,
        provider=AuthProvider.ENTRA,
        provider_subject=entra_subject,
        email_normalized=normalized_email,
    )
    update_user_profile(
        session,
        user=user,
        user_type=UserType.INTERNAL,
        display_name=display_name,
        email=normalized_email,
    )
    return user


async def signup_email_user(
    session: Session,
    *,
    email: str,
    password: str,
    display_name: str | None,
) -> User:
    validate_password_policy(password)
    password_hash = hash_password(password)
    normalized_email = normalize_email(email)
    existing_user = get_user_by_email(session, normalized_email)

    if existing_user is None:
        user = create_user(
            session,
            email=normalized_email,
            user_type=UserType.EXTERNAL,
            display_name=display_name,
        )
        create_identity(
            session,
            user_id=user.id,
            provider=AuthProvider.EMAIL,
            provider_subject=normalized_email,
            email_normalized=normalized_email,
            password_hash=password_hash,
        )
        return user

    entra_identity = get_identity_by_user_and_provider(
        session, existing_user.id, AuthProvider.ENTRA
    )
    if entra_identity:
        raise AuthConflictError(
            code=AuthConflictCode.ENTRA_ACCOUNT_ALREADY_EXISTS,
            message="Email signup is rejected because Entra account already exists",
        )

    email_identity = get_identity_by_user_and_provider(
        session, existing_user.id, AuthProvider.EMAIL
    )
    if email_identity:
        if email_identity.email_verified_at is None:
            update_password_hash(
                session,
                identity=email_identity,
                password_hash=password_hash,
            )
            update_user_profile(
                session,
                user=existing_user,
                user_type=UserType.EXTERNAL,
                display_name=display_name,
                email=normalized_email,
            )
            return existing_user

        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_ACCOUNT_ALREADY_EXISTS,
            message="Email signup is rejected because email account already exists",
        )

    create_identity(
        session,
        user_id=existing_user.id,
        provider=AuthProvider.EMAIL,
        provider_subject=normalized_email,
        email_normalized=normalized_email,
        password_hash=password_hash,
    )
    update_user_profile(
        session,
        user=existing_user,
        user_type=UserType.EXTERNAL,
        display_name=display_name,
    )
    return existing_user


async def resolve_email_login(
    session: Session,
    *,
    email: str,
    password: str,
) -> User:
    normalized_email = normalize_email(email)
    identity = get_identity_by_provider_and_email(
        session,
        provider=AuthProvider.EMAIL,
        email_normalized=normalized_email,
    )
    if identity is None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Email identity is not found",
        )

    now = datetime.now(timezone.utc)
    locked_until = ensure_utc_datetime(identity.locked_until)
    if locked_until is not None and locked_until > now:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_ACCOUNT_LOCKED,
            message="Email account is temporarily locked",
        )

    if identity.email_verified_at is None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_NOT_VERIFIED,
            message="Email is not verified",
        )
    if not identity.password_hash:
        raise AuthConflictError(
            code=AuthConflictCode.INVALID_CREDENTIALS,
            message="Password credential is not configured",
        )

    if not verify_password(password, identity.password_hash):
        settings = get_settings()
        record_failed_email_login(
            session,
            identity=identity,
            max_failures=settings.email_login_max_failures,
            lock_minutes=settings.email_login_lock_minutes,
        )
        raise AuthConflictError(
            code=AuthConflictCode.INVALID_CREDENTIALS,
            message="Invalid email or password",
        )

    if needs_rehash(identity.password_hash):
        new_hash = hash_password(password)
        update_password_hash(session, identity=identity, password_hash=new_hash)
    reset_failed_email_login_state(session, identity=identity)

    user = get_user_by_id(session, identity.user_id)
    if user is None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Email identity exists but user is not found",
        )
    return user


async def register_email_login_failure(
    session: Session,
    *,
    email: str,
) -> None:
    normalized_email = normalize_email(email)
    identity = get_identity_by_provider_and_email(
        session,
        provider=AuthProvider.EMAIL,
        email_normalized=normalized_email,
    )
    if identity is None:
        return

    settings = get_settings()
    record_failed_email_login(
        session,
        identity=identity,
        max_failures=settings.email_login_max_failures,
        lock_minutes=settings.email_login_lock_minutes,
    )


async def register_email_login_success(
    session: Session,
    *,
    email: str,
) -> None:
    normalized_email = normalize_email(email)
    identity = get_identity_by_provider_and_email(
        session,
        provider=AuthProvider.EMAIL,
        email_normalized=normalized_email,
    )
    if identity is None:
        return
    reset_failed_email_login_state(session, identity=identity)


async def verify_email_identity(
    session: Session,
    *,
    email: str,
) -> User:
    normalized_email = normalize_email(email)
    identity = get_identity_by_provider_and_email(
        session,
        provider=AuthProvider.EMAIL,
        email_normalized=normalized_email,
    )
    if identity is None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Email identity is not found",
        )

    mark_email_verified(session, identity)
    user = get_user_by_id(session, identity.user_id)
    if user is None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Email identity exists but user is not found",
        )
    return user


async def issue_email_verification_token(
    session: Session,
    *,
    email: str,
    expires_in_minutes: int | None = None,
) -> str:
    normalized_email = normalize_email(email)
    identity = get_identity_by_provider_and_email(
        session,
        provider=AuthProvider.EMAIL,
        email_normalized=normalized_email,
    )
    if identity is None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Email identity is not found",
        )
    if identity.email_verified_at is not None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_ALREADY_VERIFIED,
            message="Email is already verified",
        )

    now = datetime.now(timezone.utc)
    revoke_active_tokens_by_identity_id(
        session, identity_id=identity.id, revoked_at=now
    )

    ttl_minutes = expires_in_minutes or get_settings().email_verification_ttl_minutes
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = now + timedelta(minutes=ttl_minutes)
    create_email_verification_token(
        session,
        identity_id=identity.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    return raw_token


async def verify_email_by_token(
    session: Session,
    *,
    token: str,
) -> User:
    token_hash = _hash_token(token)
    token_record = get_email_verification_token_by_hash(session, token_hash=token_hash)
    if token_record is None or token_record.consumed_at is not None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_VERIFICATION_TOKEN_INVALID,
            message="Email verification token is invalid",
        )

    now = datetime.now(timezone.utc)
    expires_at = ensure_utc_datetime(token_record.expires_at)
    if expires_at is not None and expires_at <= now:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_VERIFICATION_TOKEN_EXPIRED,
            message="Email verification token is expired",
        )

    identity = get_identity_by_id(session, token_record.identity_id)
    if identity is None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Email identity is not found",
        )
    if identity.provider != AuthProvider.EMAIL:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Identity provider is not email",
        )

    consume_email_verification_token(session, token=token_record, consumed_at=now)
    mark_email_verified(session, identity)

    user = get_user_by_id(session, identity.user_id)
    if user is None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Email identity exists but user is not found",
        )
    return user


async def resolve_email_verify_user_id_for_audit(
    session: Session,
    *,
    token: str,
) -> UUID | None:
    token_hash = _hash_token(token)
    token_record = get_email_verification_token_by_hash(
        session,
        token_hash=token_hash,
    )
    if token_record is None:
        return None

    identity = get_identity_by_id(session, token_record.identity_id)
    if identity is None:
        return None
    return identity.user_id


async def change_email_password(
    session: Session,
    *,
    email: str,
    current_password: str,
    new_password: str,
) -> None:
    normalized_email = normalize_email(email)
    identity = get_identity_by_provider_and_email(
        session,
        provider=AuthProvider.EMAIL,
        email_normalized=normalized_email,
    )
    if identity is None or not identity.password_hash:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Email identity is not found",
        )

    if not verify_password(current_password, identity.password_hash):
        raise AuthConflictError(
            code=AuthConflictCode.CURRENT_PASSWORD_INVALID,
            message="Current password is invalid",
        )

    validate_password_policy(new_password)
    if verify_password(new_password, identity.password_hash):
        raise AuthConflictError(
            code=AuthConflictCode.PASSWORD_REUSE_NOT_ALLOWED,
            message="New password must be different from current password",
        )

    update_password_hash(
        session,
        identity=identity,
        password_hash=hash_password(new_password),
    )
    revoke_all_user_sessions(
        session,
        user_id=identity.user_id,
        revoked_at=datetime.now(timezone.utc),
    )
    logger.info(
        "auth.audit.session.revoke_all",
        user_id=str(identity.user_id),
        reason="password_change",
    )


async def issue_password_reset_token(
    session: Session,
    *,
    email: str,
    expires_in_minutes: int | None = None,
) -> tuple[str | None, UUID | None]:
    normalized_email = normalize_email(email)
    identity = get_identity_by_provider_and_email(
        session,
        provider=AuthProvider.EMAIL,
        email_normalized=normalized_email,
    )
    if identity is None or not identity.password_hash:
        return None, None

    now = datetime.now(timezone.utc)
    revoke_active_password_reset_tokens_by_identity_id(
        session,
        identity_id=identity.id,
        revoked_at=now,
    )

    ttl_minutes = expires_in_minutes or get_settings().password_reset_ttl_minutes
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = now + timedelta(minutes=ttl_minutes)
    create_password_reset_token(
        session,
        identity_id=identity.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    return raw_token, identity.user_id


async def reset_password_by_token(
    session: Session,
    *,
    token: str,
    new_password: str,
) -> UUID:
    token_hash = _hash_token(token)
    token_record = get_password_reset_token_by_hash(session, token_hash=token_hash)
    if token_record is None or token_record.consumed_at is not None:
        raise AuthConflictError(
            code=AuthConflictCode.PASSWORD_RESET_TOKEN_INVALID,
            message="Password reset token is invalid",
        )

    now = datetime.now(timezone.utc)
    expires_at = ensure_utc_datetime(token_record.expires_at)
    if expires_at is not None and expires_at <= now:
        raise AuthConflictError(
            code=AuthConflictCode.PASSWORD_RESET_TOKEN_EXPIRED,
            message="Password reset token is expired",
        )

    identity = get_identity_by_id(session, token_record.identity_id)
    if (
        identity is None
        or identity.provider != AuthProvider.EMAIL
        or not identity.password_hash
    ):
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Email identity is not found",
        )

    validate_password_policy(new_password)
    if verify_password(new_password, identity.password_hash):
        raise AuthConflictError(
            code=AuthConflictCode.PASSWORD_REUSE_NOT_ALLOWED,
            message="New password must be different from current password",
        )

    consume_password_reset_token(session, token=token_record, consumed_at=now)
    update_password_hash(
        session,
        identity=identity,
        password_hash=hash_password(new_password),
    )
    reset_failed_email_login_state(session, identity=identity)
    revoke_all_user_sessions(
        session,
        user_id=identity.user_id,
        revoked_at=now,
    )
    logger.info(
        "auth.audit.session.revoke_all",
        user_id=str(identity.user_id),
        reason="password_reset",
    )
    return identity.user_id


async def resolve_password_reset_user_id_for_audit(
    session: Session,
    *,
    token: str,
) -> UUID | None:
    token_hash = _hash_token(token)
    token_record = get_password_reset_token_by_hash(
        session,
        token_hash=token_hash,
    )
    if token_record is None:
        return None

    identity = get_identity_by_id(session, token_record.identity_id)
    if identity is None:
        return None
    return identity.user_id
