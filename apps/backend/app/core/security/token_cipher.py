"""
機密トークンの暗号化ユーティリティ.

- Entra の access_token / refresh_token を DB 保存前に暗号化する
- 既存の平文データとの後方互換のため、非暗号化値も読み取り可能にする
"""

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
    """
    設定鍵から Fernet インスタンスを生成して返す.

    Returns:
        object: cryptography.fernet.Fernet インスタンス

    Raises:
        RuntimeError: 鍵未設定、または cryptography 未導入の場合
    """
    settings = get_settings()
    raw_key = settings.entra_token_encryption_key
    if not raw_key:
        raise RuntimeError("ENTRA_TOKEN_ENCRYPTION_KEY is not set")

    try:
        from cryptography.fernet import Fernet
    except Exception as error:  # pragma: no cover - import error handling
        raise RuntimeError(
            "cryptography package is required for token encryption"
        ) from error

    # 任意文字列の鍵から固定長バイト列を導出し、Fernet キー形式へ変換する。
    derived = hashlib.sha256(raw_key.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(derived)
    return Fernet(fernet_key)


def encrypt_token(token: str | None) -> str | None:
    """
    トークンを暗号化して保存形式で返す.

    Args:
        token: 生トークン

    Returns:
        str | None: 保存用暗号化トークン（prefix 付き）または None
    """
    if token is None:
        return None
    fernet = _get_fernet()
    encrypted = fernet.encrypt(token.encode("utf-8")).decode("utf-8")
    return f"{_ENCRYPTED_PREFIX}{encrypted}"


def decrypt_token(token: str | None) -> str | None:
    """
    保存済みトークンを復号して返す.

    Args:
        token: DB 保存値（暗号化済み or 既存平文）

    Returns:
        str | None: 生トークン

    Raises:
        RuntimeError: 暗号化トークンの復号に失敗した場合
    """
    if token is None:
        return None
    if not token.startswith(_ENCRYPTED_PREFIX):
        # 後方互換: 既存の平文保存値はそのまま扱う。
        return token
    encrypted_value = token[len(_ENCRYPTED_PREFIX) :]
    try:
        fernet = _get_fernet()
        return fernet.decrypt(encrypted_value.encode("utf-8")).decode("utf-8")
    except Exception as error:
        raise RuntimeError("Failed to decrypt Entra token") from error
