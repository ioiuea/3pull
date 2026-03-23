"""
FastAPI 向けアプリ設定ローダ.

- pydantic-settings で環境変数を読み込む
- ローカル開発では apps/backend/.env が存在する場合のみ読み込む
- 本番では環境変数注入のみで動作する
"""

from __future__ import annotations

from functools import lru_cache
from ipaddress import ip_network
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
    system_name: str = Field(
        default="threepull",
        validation_alias="SYSTEM_NAME",
    )
    applicationinsights_connection_string: str | None = Field(
        default=None,
        validation_alias="APPLICATIONINSIGHTS_CONNECTION_STRING",
    )

    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    database_default_port: int = Field(
        default=1433,
        validation_alias="DATABASE_DEFAULT_PORT",
    )
    database_access_token_scope: str = Field(
        default="https://database.windows.net/.default",
        validation_alias="DATABASE_ACCESS_TOKEN_SCOPE",
    )
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
    async_jobs_enabled: bool = Field(
        default=True,
        validation_alias="ASYNC_JOBS_ENABLED",
    )
    async_job_max_rows_per_job: int = Field(
        default=50000,
        validation_alias="ASYNC_JOB_MAX_ROWS_PER_JOB",
    )
    async_job_default_retention_days: int = Field(
        default=365,
        validation_alias="ASYNC_JOB_DEFAULT_RETENTION_DAYS",
    )
    async_job_retention_max_days: int = Field(
        default=2555,
        validation_alias="ASYNC_JOB_RETENTION_MAX_DAYS",
    )
    async_job_global_concurrency: int = Field(
        default=3,
        validation_alias="ASYNC_JOB_GLOBAL_CONCURRENCY",
    )
    async_job_per_user_concurrency: int = Field(
        default=1,
        validation_alias="ASYNC_JOB_PER_USER_CONCURRENCY",
    )
    async_job_running_timeout_seconds: int = Field(
        default=2700,
        validation_alias="ASYNC_JOB_RUNNING_TIMEOUT_SECONDS",
    )
    service_bus_namespace_fqdn: str | None = Field(
        default=None,
        validation_alias="SERVICE_BUS_NAMESPACE_FQDN",
    )
    service_bus_use_connection_string: bool = Field(
        default=False,
        validation_alias="SERVICE_BUS_USE_CONNECTION_STRING",
    )
    service_bus_connection_string: str | None = Field(
        default=None,
        validation_alias="SERVICE_BUS_CONNECTION_STRING",
    )
    auth_audit_export_queue_name: str = Field(
        default="auth-audit-export",
        validation_alias="SERVICE_BUS_AUTH_AUDIT_EXPORT_QUEUE_NAME",
    )
    auth_audit_export_task_name: str = Field(
        default="jobs.auth_audit_export",
        validation_alias="ASYNC_JOB_AUTH_AUDIT_EXPORT_TASK_NAME",
    )
    sample_wait_blob_queue_name: str = Field(
        default="sample-wait-blob",
        validation_alias="SERVICE_BUS_SAMPLE_WAIT_BLOB_QUEUE_NAME",
    )
    sample_wait_blob_task_name: str = Field(
        default="jobs.sample_wait_blob",
        validation_alias="ASYNC_JOB_SAMPLE_WAIT_BLOB_TASK_NAME",
    )
    azure_blob_account_url: str | None = Field(
        default=None,
        validation_alias="AZURE_BLOB_ACCOUNT_URL",
    )
    azure_blob_container: str = Field(
        default="async-jobs",
        validation_alias="AZURE_BLOB_CONTAINER",
    )
    azure_blob_use_connection_string: bool = Field(
        default=False,
        validation_alias="AZURE_BLOB_USE_CONNECTION_STRING",
    )
    azure_blob_connection_string: str | None = Field(
        default=None,
        validation_alias="AZURE_BLOB_CONNECTION_STRING",
    )
    redis_host: str | None = Field(default=None, validation_alias="REDIS_HOST")
    redis_port: int = Field(default=10000, validation_alias="REDIS_PORT")
    redis_ssl: bool = Field(default=True, validation_alias="REDIS_SSL")
    rate_limit_mode: Literal["observe", "enforce"] = Field(
        default="enforce",
        validation_alias="RATE_LIMIT_MODE",
    )
    rate_limit_policy_email_login_request_window_1_seconds: int = Field(
        default=60,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_LOGIN_REQUEST_WINDOW_1_SECONDS",
    )
    rate_limit_policy_email_login_request_window_1_max_requests: int = Field(
        default=10,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_LOGIN_REQUEST_WINDOW_1_MAX_REQUESTS",
    )
    rate_limit_policy_email_login_request_window_2_seconds: int = Field(
        default=300,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_LOGIN_REQUEST_WINDOW_2_SECONDS",
    )
    rate_limit_policy_email_login_request_window_2_max_requests: int = Field(
        default=30,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_LOGIN_REQUEST_WINDOW_2_MAX_REQUESTS",
    )
    rate_limit_policy_email_login_failure_window_seconds: int = Field(
        default=600,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_LOGIN_FAILURE_WINDOW_SECONDS",
    )
    rate_limit_policy_email_login_max_failures: int = Field(
        default=5,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_LOGIN_MAX_FAILURES",
    )
    rate_limit_policy_email_login_block_seconds: int = Field(
        default=900,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_LOGIN_BLOCK_SECONDS",
    )
    rate_limit_policy_email_verify_resend_window_seconds: int = Field(
        default=600,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_VERIFY_RESEND_WINDOW_SECONDS",
    )
    rate_limit_policy_email_verify_resend_max_requests: int = Field(
        default=5,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_VERIFY_RESEND_MAX_REQUESTS",
    )
    rate_limit_policy_email_verify_resend_block_seconds: int = Field(
        default=1800,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_VERIFY_RESEND_BLOCK_SECONDS",
    )
    rate_limit_policy_entra_login_request_window_1_seconds: int = Field(
        default=60,
        validation_alias="RATE_LIMIT_POLICY_ENTRA_LOGIN_REQUEST_WINDOW_1_SECONDS",
    )
    rate_limit_policy_entra_login_request_window_1_max_requests: int = Field(
        default=20,
        validation_alias="RATE_LIMIT_POLICY_ENTRA_LOGIN_REQUEST_WINDOW_1_MAX_REQUESTS",
    )
    rate_limit_policy_entra_login_request_window_2_seconds: int = Field(
        default=300,
        validation_alias="RATE_LIMIT_POLICY_ENTRA_LOGIN_REQUEST_WINDOW_2_SECONDS",
    )
    rate_limit_policy_entra_login_request_window_2_max_requests: int = Field(
        default=60,
        validation_alias="RATE_LIMIT_POLICY_ENTRA_LOGIN_REQUEST_WINDOW_2_MAX_REQUESTS",
    )
    rate_limit_policy_entra_login_block_seconds: int = Field(
        default=600,
        validation_alias="RATE_LIMIT_POLICY_ENTRA_LOGIN_BLOCK_SECONDS",
    )
    rate_limit_policy_entra_callback_request_window_1_seconds: int = Field(
        default=60,
        validation_alias="RATE_LIMIT_POLICY_ENTRA_CALLBACK_REQUEST_WINDOW_1_SECONDS",
    )
    rate_limit_policy_entra_callback_request_window_1_max_requests: int = Field(
        default=20,
        validation_alias="RATE_LIMIT_POLICY_ENTRA_CALLBACK_REQUEST_WINDOW_1_MAX_REQUESTS",
    )
    rate_limit_policy_entra_callback_request_window_2_seconds: int = Field(
        default=300,
        validation_alias="RATE_LIMIT_POLICY_ENTRA_CALLBACK_REQUEST_WINDOW_2_SECONDS",
    )
    rate_limit_policy_entra_callback_request_window_2_max_requests: int = Field(
        default=60,
        validation_alias="RATE_LIMIT_POLICY_ENTRA_CALLBACK_REQUEST_WINDOW_2_MAX_REQUESTS",
    )
    rate_limit_policy_entra_callback_failure_window_seconds: int = Field(
        default=600,
        validation_alias="RATE_LIMIT_POLICY_ENTRA_CALLBACK_FAILURE_WINDOW_SECONDS",
    )
    rate_limit_policy_entra_callback_max_failures: int = Field(
        default=10,
        validation_alias="RATE_LIMIT_POLICY_ENTRA_CALLBACK_MAX_FAILURES",
    )
    rate_limit_policy_entra_callback_block_seconds: int = Field(
        default=600,
        validation_alias="RATE_LIMIT_POLICY_ENTRA_CALLBACK_BLOCK_SECONDS",
    )
    rate_limit_policy_password_reset_request_window_seconds: int = Field(
        default=600,
        validation_alias="RATE_LIMIT_POLICY_PASSWORD_RESET_REQUEST_WINDOW_SECONDS",
    )
    rate_limit_policy_password_reset_request_max_requests: int = Field(
        default=5,
        validation_alias="RATE_LIMIT_POLICY_PASSWORD_RESET_REQUEST_MAX_REQUESTS",
    )
    rate_limit_policy_password_reset_request_block_seconds: int = Field(
        default=1800,
        validation_alias="RATE_LIMIT_POLICY_PASSWORD_RESET_REQUEST_BLOCK_SECONDS",
    )
    rate_limit_policy_password_reset_confirm_window_seconds: int = Field(
        default=600,
        validation_alias="RATE_LIMIT_POLICY_PASSWORD_RESET_CONFIRM_WINDOW_SECONDS",
    )
    rate_limit_policy_password_reset_confirm_max_requests: int = Field(
        default=10,
        validation_alias="RATE_LIMIT_POLICY_PASSWORD_RESET_CONFIRM_MAX_REQUESTS",
    )
    rate_limit_policy_password_reset_confirm_failure_window_seconds: int = Field(
        default=600,
        validation_alias="RATE_LIMIT_POLICY_PASSWORD_RESET_CONFIRM_FAILURE_WINDOW_SECONDS",
    )
    rate_limit_policy_password_reset_confirm_max_failures: int = Field(
        default=5,
        validation_alias="RATE_LIMIT_POLICY_PASSWORD_RESET_CONFIRM_MAX_FAILURES",
    )
    rate_limit_policy_password_reset_confirm_block_seconds: int = Field(
        default=1800,
        validation_alias="RATE_LIMIT_POLICY_PASSWORD_RESET_CONFIRM_BLOCK_SECONDS",
    )
    rate_limit_policy_email_signup_request_window_1_seconds: int = Field(
        default=600,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_SIGNUP_REQUEST_WINDOW_1_SECONDS",
    )
    rate_limit_policy_email_signup_request_window_1_max_requests: int = Field(
        default=3,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_SIGNUP_REQUEST_WINDOW_1_MAX_REQUESTS",
    )
    rate_limit_policy_email_signup_request_window_2_seconds: int = Field(
        default=3600,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_SIGNUP_REQUEST_WINDOW_2_SECONDS",
    )
    rate_limit_policy_email_signup_request_window_2_max_requests: int = Field(
        default=10,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_SIGNUP_REQUEST_WINDOW_2_MAX_REQUESTS",
    )
    rate_limit_policy_email_signup_failure_window_seconds: int = Field(
        default=1800,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_SIGNUP_FAILURE_WINDOW_SECONDS",
    )
    rate_limit_policy_email_signup_max_failures: int = Field(
        default=5,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_SIGNUP_MAX_FAILURES",
    )
    rate_limit_policy_email_signup_block_seconds: int = Field(
        default=1200,
        validation_alias="RATE_LIMIT_POLICY_EMAIL_SIGNUP_BLOCK_SECONDS",
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
        default="http://localhost:3000",
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
    trust_proxy_headers: bool = Field(
        default=False,
        validation_alias="TRUST_PROXY_HEADERS",
    )
    trusted_proxy_cidrs: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        validation_alias="TRUSTED_PROXY_CIDRS",
    )
    csrf_trusted_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        validation_alias="CSRF_TRUSTED_ORIGINS",
    )

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    @property
    def api_service_name(self) -> str:
        """API の service.name を返す."""
        return f"{self.system_name}-api"

    def worker_service_name(self, job_name: str) -> str:
        """worker の service.name を返す."""
        normalized_job_name = job_name.replace("_", "-")
        return f"{self.system_name}-worker-{normalized_job_name}"

    def scheduler_service_name(self, job_name: str) -> str:
        """scheduler の service.name を返す."""
        normalized_job_name = job_name.replace("_", "-")
        return f"{self.system_name}-scheduler-{normalized_job_name}"

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

    @field_validator("trusted_proxy_cidrs", mode="before")
    @classmethod
    def _parse_trusted_proxy_cidrs(cls, value: object) -> object:
        """
        TRUSTED_PROXY_CIDRS を list[str] に正規化する.
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

    @field_validator("trusted_proxy_cidrs")
    @classmethod
    def _validate_trusted_proxy_cidrs(cls, value: list[str]) -> list[str]:
        """
        TRUSTED_PROXY_CIDRS の CIDR 形式を検証する.
        """
        for cidr in value:
            ip_network(cidr, strict=False)
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

    @field_validator("database_default_port")
    @classmethod
    def _validate_database_default_port(cls, value: int) -> int:
        """DATABASE_DEFAULT_PORT の範囲を検証する."""
        if not 1 <= value <= 65_535:
            raise ValueError("DATABASE_DEFAULT_PORT must be between 1 and 65535")
        return value

    @field_validator("redis_port")
    @classmethod
    def _validate_redis_port(cls, value: int) -> int:
        """REDIS_PORT の範囲を検証する."""
        if not 1 <= value <= 65_535:
            raise ValueError("REDIS_PORT must be between 1 and 65535")
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

    @field_validator("async_job_max_rows_per_job")
    @classmethod
    def _validate_async_job_max_rows_per_job(cls, value: int) -> int:
        """
        ASYNC_JOB_MAX_ROWS_PER_JOB の範囲を検証する.

        許容範囲: 1..50000
        """
        if not 1 <= value <= 50000:
            raise ValueError("ASYNC_JOB_MAX_ROWS_PER_JOB must be between 1 and 50000")
        return value

    @field_validator("async_job_default_retention_days")
    @classmethod
    def _validate_async_job_default_retention_days(cls, value: int) -> int:
        """
        ASYNC_JOB_DEFAULT_RETENTION_DAYS の範囲を検証する.

        許容範囲: 1..2555
        """
        if not 1 <= value <= 2555:
            raise ValueError(
                "ASYNC_JOB_DEFAULT_RETENTION_DAYS must be between 1 and 2555"
            )
        return value

    @field_validator("async_job_retention_max_days")
    @classmethod
    def _validate_async_job_retention_max_days(cls, value: int) -> int:
        """
        ASYNC_JOB_RETENTION_MAX_DAYS の範囲を検証する.

        許容範囲: 1..2555
        """
        if not 1 <= value <= 2555:
            raise ValueError("ASYNC_JOB_RETENTION_MAX_DAYS must be between 1 and 2555")
        return value

    @field_validator("async_job_global_concurrency")
    @classmethod
    def _validate_async_job_global_concurrency(cls, value: int) -> int:
        """ASYNC_JOB_GLOBAL_CONCURRENCY の範囲を検証する."""
        if value < 1:
            raise ValueError(
                "ASYNC_JOB_GLOBAL_CONCURRENCY must be greater than or equal to 1"
            )
        return value

    @field_validator("async_job_per_user_concurrency")
    @classmethod
    def _validate_async_job_per_user_concurrency(cls, value: int) -> int:
        """ASYNC_JOB_PER_USER_CONCURRENCY の範囲を検証する."""
        if value < 1:
            raise ValueError(
                "ASYNC_JOB_PER_USER_CONCURRENCY must be greater than or equal to 1"
            )
        return value

    @field_validator("async_job_running_timeout_seconds")
    @classmethod
    def _validate_async_job_running_timeout_seconds(cls, value: int) -> int:
        """ASYNC_JOB_RUNNING_TIMEOUT_SECONDS の範囲を検証する."""
        if value < 1:
            raise ValueError(
                "ASYNC_JOB_RUNNING_TIMEOUT_SECONDS must be greater than or equal to 1"
            )
        return value

    @model_validator(mode="after")
    def _validate_async_job_retention_consistency(self) -> AppSettings:
        """
        async job retention の相関制約を検証する.
        """
        if self.async_job_default_retention_days > self.async_job_retention_max_days:
            raise ValueError(
                "ASYNC_JOB_DEFAULT_RETENTION_DAYS must be less than or equal to "
                "ASYNC_JOB_RETENTION_MAX_DAYS"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """LRU キャッシュで単一化した設定インスタンスを返す。"""
    return AppSettings()
