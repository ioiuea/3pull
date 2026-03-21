"""Argon2id ベースのパスワードハッシュユーティリティ."""

from __future__ import annotations

from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.settings import get_settings


@lru_cache(maxsize=1)
def get_password_hasher() -> PasswordHasher:
    """設定値を反映した Argon2id ハッシャーを返す."""
    settings = get_settings()
    return PasswordHasher(
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_cost,
        parallelism=settings.argon2_parallelism,
        hash_len=settings.argon2_hash_len,
        salt_len=settings.argon2_salt_len,
    )


def hash_password(password: str) -> str:
    """生パスワードを Argon2id でハッシュ化する."""
    return get_password_hasher().hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """生パスワードと保存済みハッシュを検証する."""
    try:
        return get_password_hasher().verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """保存済みハッシュが現在設定で再ハッシュ必要かを判定する."""
    return get_password_hasher().check_needs_rehash(password_hash)
