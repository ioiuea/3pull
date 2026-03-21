"""機密トークンの暗号化ユーティリティ."""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from typing import Protocol

from app.core.settings import get_settings

_ENCRYPTED_PREFIX = "enc:v1:"


class _TokenCipher(Protocol):
    """encrypt/decrypt を提供する暗号化インターフェース."""

    def encrypt(self, data: bytes) -> bytes: ...

    def decrypt(self, token: bytes, ttl: int | None = None) -> bytes: ...


@lru_cache(maxsize=1)
def _get_fernet() -> _TokenCipher:
    """設定鍵から Fernet インスタンスを生成して返す."""
    settings = get_settings()
    raw_key = settings.entra_token_encryption_key
    if not raw_key:
        raise RuntimeError("ENTRA_TOKEN_ENCRYPTION_KEY is not set")

    try:
        from cryptography.fernet import Fernet
    except Exception as error:  # pragma: no cover
        raise RuntimeError(
            "cryptography package is required for token encryption"
        ) from error

    derived = hashlib.sha256(raw_key.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(derived)
    return Fernet(fernet_key)


def encrypt_token(token: str | None) -> str | None:
    """トークンを暗号化して保存形式で返す."""
    if token is None:
        return None
    fernet = _get_fernet()
    encrypted = fernet.encrypt(token.encode("utf-8")).decode("utf-8")
    return f"{_ENCRYPTED_PREFIX}{encrypted}"


def decrypt_token(token: str | None) -> str | None:
    """保存済みトークンを復号して返す."""
    if token is None:
        return None
    if not token.startswith(_ENCRYPTED_PREFIX):
        return token
    encrypted_value = token[len(_ENCRYPTED_PREFIX) :]
    try:
        fernet = _get_fernet()
        return fernet.decrypt(encrypted_value.encode("utf-8")).decode("utf-8")
    except Exception as error:
        raise RuntimeError("Failed to decrypt Entra token") from error
