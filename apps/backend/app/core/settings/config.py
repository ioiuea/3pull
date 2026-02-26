"""
FastAPI 向けアプリ設定ローダ.

- pydantic-settings で環境変数を読み込む
- ローカル開発では apps/backend/.env が存在する場合のみ読み込む
- 本番では環境変数注入のみで動作する
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _load_dotenv_if_present(root_env_path: Path) -> None:
    """
    `.env` が存在する場合のみ dotenv を読み込む.

    python-dotenv 未導入または .env 不在時は何もせずに返す。

    Args:
        root_env_path: apps/backend/.env の絶対パス
    """
    if not root_env_path.exists():
        return

    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return

    # 既存の環境変数を優先し、dotenv で上書きしない。
    load_dotenv(dotenv_path=root_env_path, override=False)


# apps/backend/app/core/settings/config.py から 3 つ上が apps/backend/
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"
_load_dotenv_if_present(_ROOT_ENV)


class AppSettings(BaseSettings):
    """環境変数から解決されるアプリ設定。"""

    api_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        validation_alias="API_LOG_LEVEL",
    )

    service_name: str = Field(
        default="3pull-api",
        validation_alias="SERVICE_NAME",
    )

    api_port: int = Field(default=8000, validation_alias="API_PORT")

    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    database_echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")
    database_pool_size: int = Field(default=5, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(
        default=10, validation_alias="DATABASE_MAX_OVERFLOW"
    )
    database_pool_timeout: int = Field(
        default=30, validation_alias="DATABASE_POOL_TIMEOUT"
    )
    email_verification_ttl_minutes: int = Field(
        default=60,
        validation_alias="EMAIL_VERIFICATION_TTL_MINUTES",
    )
    password_reset_ttl_minutes: int = Field(
        default=60,
        validation_alias="PASSWORD_RESET_TTL_MINUTES",
    )
    email_login_max_failures: int = Field(
        default=5, validation_alias="EMAIL_LOGIN_MAX_FAILURES"
    )
    email_login_lock_minutes: int = Field(
        default=15, validation_alias="EMAIL_LOGIN_LOCK_MINUTES"
    )
    argon2_time_cost: int = Field(default=3, validation_alias="ARGON2_TIME_COST")
    argon2_memory_cost: int = Field(
        default=65536, validation_alias="ARGON2_MEMORY_COST"
    )
    argon2_parallelism: int = Field(default=4, validation_alias="ARGON2_PARALLELISM")
    argon2_hash_len: int = Field(default=32, validation_alias="ARGON2_HASH_LEN")
    argon2_salt_len: int = Field(default=16, validation_alias="ARGON2_SALT_LEN")
    session_ttl_seconds: int = Field(
        default=604800,
        validation_alias="SESSION_TTL_SECONDS",
    )
    session_expired_grace_days: int = Field(
        default=3,
        validation_alias="SESSION_EXPIRED_GRACE_DAYS",
    )
    auth_audit_retention_days: int = Field(
        default=365,
        validation_alias="AUTH_AUDIT_RETENTION_DAYS",
    )
    session_cleanup_enabled: bool = Field(
        default=True,
        validation_alias="SESSION_CLEANUP_ENABLED",
    )
    audit_cleanup_enabled: bool = Field(
        default=True,
        validation_alias="AUDIT_CLEANUP_ENABLED",
    )
    cleanup_batch_size: int = Field(
        default=5000,
        validation_alias="CLEANUP_BATCH_SIZE",
    )
    session_cookie_name: str = Field(
        default="app_session", validation_alias="SESSION_COOKIE_NAME"
    )
    session_cookie_secure: bool = Field(
        default=True, validation_alias="SESSION_COOKIE_SECURE"
    )
    session_cookie_samesite: Literal["lax", "strict", "none"] = Field(
        default="lax",
        validation_alias="SESSION_COOKIE_SAMESITE",
    )
    session_secret_key: str = Field(
        default="dev-only-change-me",
        validation_alias="SESSION_SECRET_KEY",
    )
    auth_debug_return_tokens: bool = Field(
        default=False,
        validation_alias="AUTH_DEBUG_RETURN_TOKENS",
    )
    frontend_base_url: str = Field(
        default="http://localhost:5173",
        validation_alias="FRONTEND_BASE_URL",
    )
    auth_post_login_default_path: str = Field(
        default="/en",
        validation_alias="AUTH_POST_LOGIN_DEFAULT_PATH",
    )
    entra_tenant_id: str | None = Field(
        default=None, validation_alias="ENTRA_TENANT_ID"
    )
    entra_client_id: str | None = Field(
        default=None, validation_alias="ENTRA_CLIENT_ID"
    )
    entra_client_secret: str | None = Field(
        default=None, validation_alias="ENTRA_CLIENT_SECRET"
    )
    entra_token_encryption_key: str | None = Field(
        default=None,
        validation_alias="ENTRA_TOKEN_ENCRYPTION_KEY",
    )
    entra_redirect_uri: str | None = Field(
        default=None, validation_alias="ENTRA_REDIRECT_URI"
    )
    entra_internal_domains: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        validation_alias="ENTRA_INTERNAL_DOMAINS",
    )
    csrf_trusted_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        validation_alias="CSRF_TRUSTED_ORIGINS",
    )

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    @field_validator("csrf_trusted_origins", mode="before")
    @classmethod
    def _parse_csrf_trusted_origins(cls, value: object) -> object:
        """
        CSRF_TRUSTED_ORIGINS を list[str] に正規化する.

        環境変数ではカンマ区切り文字列の入力を許容する。

        Args:
            value: 設定入力値

        Returns:
            object: 正規化後の値
        """
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("entra_internal_domains", mode="before")
    @classmethod
    def _parse_entra_internal_domains(cls, value: object) -> object:
        """
        ENTRA_INTERNAL_DOMAINS を list[str] に正規化する.

        環境変数ではカンマ区切り文字列の入力を許容する。

        Args:
            value: 設定入力値

        Returns:
            object: 正規化後の値
        """
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return value

    @field_validator("session_ttl_seconds")
    @classmethod
    def _validate_session_ttl_seconds(cls, value: int) -> int:
        """
        SESSION_TTL_SECONDS の範囲を検証する.

        許容範囲: 3600..2592000（1時間..30日）
        """
        if not 3600 <= value <= 2592000:
            raise ValueError("SESSION_TTL_SECONDS must be between 3600 and 2592000")
        return value

    @field_validator("session_expired_grace_days")
    @classmethod
    def _validate_session_expired_grace_days(cls, value: int) -> int:
        """
        SESSION_EXPIRED_GRACE_DAYS の範囲を検証する.

        許容範囲: 0..7
        """
        if not 0 <= value <= 7:
            raise ValueError("SESSION_EXPIRED_GRACE_DAYS must be between 0 and 7")
        return value

    @field_validator("auth_audit_retention_days")
    @classmethod
    def _validate_auth_audit_retention_days(cls, value: int) -> int:
        """
        AUTH_AUDIT_RETENTION_DAYS の範囲を検証する.

        許容範囲: 1..2555（約7年）
        """
        if not 1 <= value <= 2555:
            raise ValueError("AUTH_AUDIT_RETENTION_DAYS must be between 1 and 2555")
        return value

    @field_validator("cleanup_batch_size")
    @classmethod
    def _validate_cleanup_batch_size(cls, value: int) -> int:
        """
        CLEANUP_BATCH_SIZE の範囲を検証する.

        許容範囲: 100..50000
        """
        if not 100 <= value <= 50000:
            raise ValueError("CLEANUP_BATCH_SIZE must be between 100 and 50000")
        return value


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """LRU キャッシュで単一化した設定インスタンスを返す。"""
    return AppSettings()
