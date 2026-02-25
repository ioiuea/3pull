"""
認証アカウント統合ポリシーを扱うサービス.

- Entra 優先の統合ルールを実装する
- Email signup の拒否条件を実装する
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging.config import get_logger
from app.models.auth.auth_identity import AuthProvider
from app.models.auth.user import User, UserType
from app.core.security.password import hash_password, needs_rehash, verify_password
from app.core.settings import get_settings
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
    """認証アカウント競合コード."""

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
    """
    認証アカウント競合を表す例外.

    Attributes:
        code: 競合種別コード
        message: 人間可読メッセージ
    """

    code: AuthConflictCode
    message: str


logger = get_logger(__name__)


def _hash_token(raw_token: str) -> str:
    """
    生トークンを SHA-256 でハッシュ化する.

    Args:
        raw_token: 生トークン文字列

    Returns:
        str: 16進文字列ハッシュ
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def validate_password_policy(password: str) -> None:
    """
    Email signup 用パスワードポリシーを検証する.

    ポリシー:
    - 最低 10 文字
    - 英大文字 / 英小文字 / 数字 / 記号 のうち 3 種以上を含む

    Args:
        password: 入力パスワード（生文字列）

    Raises:
        AuthConflictError: ポリシー未満の場合
    """
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
    session: AsyncSession,
    *,
    user_principal_name: str,
    entra_subject: str,
    display_name: str | None,
) -> User:
    """
    Entra ログイン時のユーザー解決を行う.

    ルール:
    - Entra 既存アイデンティティがあればそのユーザーを返す
    - 先に Email 登録済みなら Email アイデンティティを削除して Entra に統合する
    - ユーザーが未作成なら internal ユーザーとして新規作成する

    Args:
        session: DB セッション
        user_principal_name: Entra 側 UPN（users.email に保存する）
        entra_subject: Entra 側 subject（oid/sub）
        display_name: 表示名

    Returns:
        User: ログイン解決後のユーザー
    """
    normalized_email = normalize_email(user_principal_name)

    existing_entra_identity = await get_identity_by_provider_subject(
        session,
        provider=AuthProvider.ENTRA,
        provider_subject=entra_subject,
    )
    if existing_entra_identity:
        user = await get_user_by_id(session, existing_entra_identity.user_id)
        if user is None:
            raise AuthConflictError(
                code=AuthConflictCode.ENTRA_SUBJECT_CONFLICT,
                message="Entra identity exists but user is not found",
            )
        await update_user_profile(
            session,
            user=user,
            user_type=UserType.INTERNAL,
            display_name=display_name,
            email=normalized_email,
        )
        return user

    user = await get_user_by_email(session, normalized_email)
    if user is None:
        user = await create_user(
            session,
            email=normalized_email,
            user_type=UserType.INTERNAL,
            display_name=display_name,
        )
        await create_identity(
            session,
            user_id=user.id,
            provider=AuthProvider.ENTRA,
            provider_subject=entra_subject,
            email_normalized=normalized_email,
        )
        return user

    entra_identity_for_user = await get_identity_by_user_and_provider(
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
        await update_user_profile(
            session,
            user=user,
            user_type=UserType.INTERNAL,
            display_name=display_name,
            email=normalized_email,
        )
        return user

    # Entra 優先ルール:
    # 先に Email 登録済みなら Email identity を撤去し Entra identity へ統合する。
    email_identity = await get_identity_by_user_and_provider(
        session, user.id, AuthProvider.EMAIL
    )
    if email_identity:
        await delete_identity_by_id(session, email_identity.id)

    await create_identity(
        session,
        user_id=user.id,
        provider=AuthProvider.ENTRA,
        provider_subject=entra_subject,
        email_normalized=normalized_email,
    )
    await update_user_profile(
        session,
        user=user,
        user_type=UserType.INTERNAL,
        display_name=display_name,
        email=normalized_email,
    )
    return user


async def signup_email_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str | None,
) -> User:
    """
    Email signup のユーザー登録を行う.

    ルール:
    - すでに Entra identity がある同一メールは登録拒否する
    - すでに Email identity がある同一メールも登録拒否する
    - 未登録なら external ユーザー + Email identity を作成する

    Args:
        session: DB セッション
        email: 登録メール
        password: 生パスワード（ポリシー検証用）
        display_name: 表示名

    Returns:
        User: 作成または解決されたユーザー
    """
    validate_password_policy(password)
    password_hash = hash_password(password)
    normalized_email = normalize_email(email)
    existing_user = await get_user_by_email(session, normalized_email)

    if existing_user is None:
        user = await create_user(
            session,
            email=normalized_email,
            user_type=UserType.EXTERNAL,
            display_name=display_name,
        )
        await create_identity(
            session,
            user_id=user.id,
            provider=AuthProvider.EMAIL,
            provider_subject=normalized_email,
            email_normalized=normalized_email,
            password_hash=password_hash,
        )
        return user

    entra_identity = await get_identity_by_user_and_provider(
        session, existing_user.id, AuthProvider.ENTRA
    )
    if entra_identity:
        raise AuthConflictError(
            code=AuthConflictCode.ENTRA_ACCOUNT_ALREADY_EXISTS,
            message="Email signup is rejected because Entra account already exists",
        )

    email_identity = await get_identity_by_user_and_provider(
        session, existing_user.id, AuthProvider.EMAIL
    )
    if email_identity:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_ACCOUNT_ALREADY_EXISTS,
            message="Email signup is rejected because email account already exists",
        )

    await create_identity(
        session,
        user_id=existing_user.id,
        provider=AuthProvider.EMAIL,
        provider_subject=normalized_email,
        email_normalized=normalized_email,
        password_hash=password_hash,
    )
    await update_user_profile(
        session,
        user=existing_user,
        user_type=UserType.EXTERNAL,
        display_name=display_name,
    )
    return existing_user


async def resolve_email_login(
    session: AsyncSession,
    *,
    email: str,
    password: str,
) -> User:
    """
    Email login 時のユーザー解決を行う.

    ルール:
    - Email identity が存在しない場合は失敗
    - email_verified_at が未設定の場合は失敗（検証完了までログイン不可）

    Args:
        session: DB セッション
        email: ログイン対象メール
        password: 生パスワード

    Returns:
        User: ログイン対象ユーザー
    """
    normalized_email = normalize_email(email)
    identity = await get_identity_by_provider_and_email(
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
    if identity.locked_until is not None and identity.locked_until > now:
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
        await record_failed_email_login(
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
        await update_password_hash(session, identity=identity, password_hash=new_hash)
    await reset_failed_email_login_state(session, identity=identity)

    user = await get_user_by_id(session, identity.user_id)
    if user is None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Email identity exists but user is not found",
        )
    return user


async def register_email_login_failure(
    session: AsyncSession,
    *,
    email: str,
) -> None:
    """
    Email ログイン失敗を記録し、必要に応じてロック状態へ遷移させる.

    Args:
        session: DB セッション
        email: ログイン対象メール
    """
    normalized_email = normalize_email(email)
    identity = await get_identity_by_provider_and_email(
        session,
        provider=AuthProvider.EMAIL,
        email_normalized=normalized_email,
    )
    if identity is None:
        return

    settings = get_settings()
    await record_failed_email_login(
        session,
        identity=identity,
        max_failures=settings.email_login_max_failures,
        lock_minutes=settings.email_login_lock_minutes,
    )


async def register_email_login_success(
    session: AsyncSession,
    *,
    email: str,
) -> None:
    """
    Email ログイン成功時に失敗カウントとロック状態を解除する.

    Args:
        session: DB セッション
        email: ログイン対象メール
    """
    normalized_email = normalize_email(email)
    identity = await get_identity_by_provider_and_email(
        session,
        provider=AuthProvider.EMAIL,
        email_normalized=normalized_email,
    )
    if identity is None:
        return
    await reset_failed_email_login_state(session, identity=identity)


async def verify_email_identity(
    session: AsyncSession,
    *,
    email: str,
) -> User:
    """
    Email 検証完了処理を行い、対応ユーザーを返す.

    Args:
        session: DB セッション
        email: 検証対象メール

    Returns:
        User: 検証完了後のユーザー
    """
    normalized_email = normalize_email(email)
    identity = await get_identity_by_provider_and_email(
        session,
        provider=AuthProvider.EMAIL,
        email_normalized=normalized_email,
    )
    if identity is None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Email identity is not found",
        )

    await mark_email_verified(session, identity)
    user = await get_user_by_id(session, identity.user_id)
    if user is None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Email identity exists but user is not found",
        )
    return user


async def issue_email_verification_token(
    session: AsyncSession,
    *,
    email: str,
    expires_in_minutes: int | None = None,
) -> str:
    """
    Email identity 向け検証トークンを発行する.

    - 同一 identity の未消費トークンは新規発行時に失効する
    - すでに検証済みの場合は発行しない

    Args:
        session: DB セッション
        email: 対象メール
        expires_in_minutes: トークン有効期限（分）。未指定時は設定値を利用

    Returns:
        str: メール送信用の生トークン
    """
    normalized_email = normalize_email(email)
    identity = await get_identity_by_provider_and_email(
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
    await revoke_active_tokens_by_identity_id(
        session, identity_id=identity.id, revoked_at=now
    )

    ttl_minutes = expires_in_minutes or get_settings().email_verification_ttl_minutes
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = now + timedelta(minutes=ttl_minutes)
    await create_email_verification_token(
        session,
        identity_id=identity.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    return raw_token


async def verify_email_by_token(
    session: AsyncSession,
    *,
    token: str,
) -> User:
    """
    メール検証トークンを消費して検証完了処理を行う.

    Args:
        session: DB セッション
        token: 生トークン

    Returns:
        User: 検証完了後ユーザー
    """
    token_hash = _hash_token(token)
    token_record = await get_email_verification_token_by_hash(
        session, token_hash=token_hash
    )
    if token_record is None or token_record.consumed_at is not None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_VERIFICATION_TOKEN_INVALID,
            message="Email verification token is invalid",
        )

    now = datetime.now(timezone.utc)
    if token_record.expires_at <= now:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_VERIFICATION_TOKEN_EXPIRED,
            message="Email verification token is expired",
        )

    identity = await get_identity_by_id(session, token_record.identity_id)
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

    await consume_email_verification_token(session, token=token_record, consumed_at=now)
    await mark_email_verified(session, identity)

    user = await get_user_by_id(session, identity.user_id)
    if user is None:
        raise AuthConflictError(
            code=AuthConflictCode.EMAIL_IDENTITY_NOT_FOUND,
            message="Email identity exists but user is not found",
        )
    return user


async def change_email_password(
    session: AsyncSession,
    *,
    email: str,
    current_password: str,
    new_password: str,
) -> None:
    """
    Email 認証ユーザーのパスワードを変更する.

    ルール:
    - 旧パスワードの検証に成功した場合のみ更新可能
    - 新パスワードは既存ポリシーを満たす必要がある
    - 同一パスワードへの更新は禁止する

    Args:
        session: DB セッション
        email: 対象メール
        current_password: 現在の生パスワード
        new_password: 新しい生パスワード
    """
    normalized_email = normalize_email(email)
    identity = await get_identity_by_provider_and_email(
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

    await update_password_hash(
        session,
        identity=identity,
        password_hash=hash_password(new_password),
    )
    await revoke_all_user_sessions(
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
    session: AsyncSession,
    *,
    email: str,
    expires_in_minutes: int | None = None,
) -> str | None:
    """
    パスワードリセットトークンを発行する.

    仕様:
    - アカウント列挙耐性のため、対象が存在しない場合は None を返す
    - 同一 identity の未消費トークンは新規発行時に失効する

    Args:
        session: DB セッション
        email: 対象メール
        expires_in_minutes: トークン有効期限（分）。未指定時は設定値を利用

    Returns:
        str | None: メール送信用の生トークン。対象がなければ None
    """
    normalized_email = normalize_email(email)
    identity = await get_identity_by_provider_and_email(
        session,
        provider=AuthProvider.EMAIL,
        email_normalized=normalized_email,
    )
    if identity is None or not identity.password_hash:
        return None

    now = datetime.now(timezone.utc)
    await revoke_active_password_reset_tokens_by_identity_id(
        session,
        identity_id=identity.id,
        revoked_at=now,
    )

    ttl_minutes = expires_in_minutes or get_settings().password_reset_ttl_minutes
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = now + timedelta(minutes=ttl_minutes)
    await create_password_reset_token(
        session,
        identity_id=identity.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    return raw_token


async def reset_password_by_token(
    session: AsyncSession,
    *,
    token: str,
    new_password: str,
) -> None:
    """
    リセットトークンを消費してパスワードを再設定する.

    Args:
        session: DB セッション
        token: 生リセットトークン
        new_password: 新しい生パスワード
    """
    token_hash = _hash_token(token)
    token_record = await get_password_reset_token_by_hash(
        session, token_hash=token_hash
    )
    if token_record is None or token_record.consumed_at is not None:
        raise AuthConflictError(
            code=AuthConflictCode.PASSWORD_RESET_TOKEN_INVALID,
            message="Password reset token is invalid",
        )

    now = datetime.now(timezone.utc)
    if token_record.expires_at <= now:
        raise AuthConflictError(
            code=AuthConflictCode.PASSWORD_RESET_TOKEN_EXPIRED,
            message="Password reset token is expired",
        )

    identity = await get_identity_by_id(session, token_record.identity_id)
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

    await consume_password_reset_token(session, token=token_record, consumed_at=now)
    await update_password_hash(
        session,
        identity=identity,
        password_hash=hash_password(new_password),
    )
    await reset_failed_email_login_state(session, identity=identity)
    await revoke_all_user_sessions(
        session,
        user_id=identity.user_id,
        revoked_at=now,
    )
    logger.info(
        "auth.audit.session.revoke_all",
        user_id=str(identity.user_id),
        reason="password_reset",
    )
