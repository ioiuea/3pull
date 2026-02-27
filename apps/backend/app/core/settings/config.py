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

from pydantic import Field, field_validator, model_validator
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
    session_ttl_hours: int = Field(
        default=168,
        validation_alias="SESSION_TTL_HOURS",
    )
    session_expired_grace_days: int = Field(
        default=3,
        validation_alias="SESSION_EXPIRED_GRACE_DAYS",
    )
    auth_audit_retention_months: int = Field(
        default=12,
        validation_alias="AUTH_AUDIT_RETENTION_MONTHS",
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
    celery_enabled: bool = Field(
        default=True,
        validation_alias="CELERY_ENABLED",
    )
    celery_broker_url: str | None = Field(
        default=None,
        validation_alias="CELERY_BROKER_URL",
    )
    celery_result_backend_url: str | None = Field(
        default=None,
        validation_alias="CELERY_RESULT_BACKEND_URL",
    )
    celery_max_rows_per_job: int = Field(
        default=50000,
        validation_alias="CELERY_MAX_ROWS_PER_JOB",
    )
    celery_default_retention_days: int = Field(
        default=365,
        validation_alias="CELERY_DEFAULT_RETENTION_DAYS",
    )
    celery_retention_max_days: int = Field(
        default=2555,
        validation_alias="CELERY_RETENTION_MAX_DAYS",
    )
    celery_global_concurrency: int = Field(
        default=3,
        validation_alias="CELERY_GLOBAL_CONCURRENCY",
    )
    celery_per_user_concurrency: int = Field(
        default=1,
        validation_alias="CELERY_PER_USER_CONCURRENCY",
    )
    celery_task_time_limit_seconds: int = Field(
        default=1800,
        validation_alias="CELERY_TASK_TIME_LIMIT_SECONDS",
    )
    celery_task_modules: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "app.workers.audit_export_tasks",
            "app.workers.sample_wait_blob_tasks",
        ],
        validation_alias="CELERY_TASK_MODULES",
    )
    auth_audit_export_queue_name: str = Field(
        default="auth_audit_exports",
        validation_alias="CELERY_AUTH_AUDIT_EXPORT_QUEUE_NAME",
    )
    auth_audit_export_task_name: str = Field(
        default="jobs.auth_audit_export",
        validation_alias="CELERY_AUTH_AUDIT_EXPORT_TASK_NAME",
    )
    sample_wait_blob_queue_name: str = Field(
        default="sample_wait_blob",
        validation_alias="CELERY_SAMPLE_WAIT_BLOB_QUEUE_NAME",
    )
    sample_wait_blob_task_name: str = Field(
        default="jobs.sample_wait_blob",
        validation_alias="CELERY_SAMPLE_WAIT_BLOB_TASK_NAME",
    )
    azure_blob_account_url: str | None = Field(
        default=None,
        validation_alias="AZURE_BLOB_ACCOUNT_URL",
    )
    azure_blob_container: str = Field(
        default="async-jobs",
        validation_alias="AZURE_BLOB_CONTAINER",
    )
    azure_blob_credential: str | None = Field(
        default=None,
        validation_alias="AZURE_BLOB_CREDENTIAL",
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

    @field_validator("celery_task_modules", mode="before")
    @classmethod
    def _parse_celery_task_modules(cls, value: object) -> object:
        """
        CELERY_TASK_MODULES を list[str] に正規化する.

        環境変数ではカンマ区切り文字列の入力を許容する。
        """
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("session_ttl_hours")
    @classmethod
    def _validate_session_ttl_hours(cls, value: int) -> int:
        """
        SESSION_TTL_HOURS の範囲を検証する.

        許容範囲: 1..720（1時間..30日）
        """
        if not 1 <= value <= 720:
            raise ValueError("SESSION_TTL_HOURS must be between 1 and 720")
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

    @field_validator("auth_audit_retention_months")
    @classmethod
    def _validate_auth_audit_retention_months(cls, value: int) -> int:
        """
        AUTH_AUDIT_RETENTION_MONTHS の範囲を検証する.

        許容範囲: 1..84（1か月..7年）
        """
        if not 1 <= value <= 84:
            raise ValueError("AUTH_AUDIT_RETENTION_MONTHS must be between 1 and 84")
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

    @field_validator("celery_max_rows_per_job")
    @classmethod
    def _validate_celery_max_rows_per_job(cls, value: int) -> int:
        """
        CELERY_MAX_ROWS_PER_JOB の範囲を検証する.

        許容範囲: 1..50000
        """
        if not 1 <= value <= 50000:
            raise ValueError("CELERY_MAX_ROWS_PER_JOB must be between 1 and 50000")
        return value

    @field_validator("celery_default_retention_days")
    @classmethod
    def _validate_celery_default_retention_days(cls, value: int) -> int:
        """
        CELERY_DEFAULT_RETENTION_DAYS の範囲を検証する.

        許容範囲: 1..2555
        """
        if not 1 <= value <= 2555:
            raise ValueError("CELERY_DEFAULT_RETENTION_DAYS must be between 1 and 2555")
        return value

    @field_validator("celery_retention_max_days")
    @classmethod
    def _validate_celery_retention_max_days(cls, value: int) -> int:
        """
        CELERY_RETENTION_MAX_DAYS の範囲を検証する.

        許容範囲: 1..2555
        """
        if not 1 <= value <= 2555:
            raise ValueError("CELERY_RETENTION_MAX_DAYS must be between 1 and 2555")
        return value

    @field_validator("celery_global_concurrency")
    @classmethod
    def _validate_celery_global_concurrency(cls, value: int) -> int:
        """CELERY_GLOBAL_CONCURRENCY の範囲を検証する."""
        if value < 1:
            raise ValueError(
                "CELERY_GLOBAL_CONCURRENCY must be greater than or equal to 1"
            )
        return value

    @field_validator("celery_per_user_concurrency")
    @classmethod
    def _validate_celery_per_user_concurrency(cls, value: int) -> int:
        """CELERY_PER_USER_CONCURRENCY の範囲を検証する."""
        if value < 1:
            raise ValueError(
                "CELERY_PER_USER_CONCURRENCY must be greater than or equal to 1"
            )
        return value

    @field_validator("celery_task_time_limit_seconds")
    @classmethod
    def _validate_celery_task_time_limit_seconds(cls, value: int) -> int:
        """CELERY_TASK_TIME_LIMIT_SECONDS の範囲を検証する."""
        if value < 1:
            raise ValueError(
                "CELERY_TASK_TIME_LIMIT_SECONDS must be greater than or equal to 1"
            )
        return value

    @model_validator(mode="after")
    def _validate_celery_retention_consistency(self) -> AppSettings:
        """
        celery retention の相関制約を検証する.
        """
        if self.celery_default_retention_days > self.celery_retention_max_days:
            raise ValueError(
                "CELERY_DEFAULT_RETENTION_DAYS must be less than or equal to "
                "CELERY_RETENTION_MAX_DAYS"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """LRU キャッシュで単一化した設定インスタンスを返す。"""
    return AppSettings()
