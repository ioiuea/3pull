from app.core.settings.config import AppSettings


def test_async_job_settings_accept_new_env_names() -> None:
    # 目的: 非同期ジョブ設定が新しい ASYNC_JOB_/SERVICE_BUS_ 名で読めることを保証する。
    # 条件: 新名称の環境変数を AppSettings に渡す。
    # 期待値: 各設定が対応する属性へ正しく反映される。
    settings = AppSettings(
        ASYNC_JOBS_ENABLED=False,
        ASYNC_JOB_MAX_ROWS_PER_JOB=1234,
        ASYNC_JOB_DEFAULT_RETENTION_DAYS=90,
        ASYNC_JOB_RETENTION_MAX_DAYS=365,
        ASYNC_JOB_GLOBAL_CONCURRENCY=4,
        ASYNC_JOB_PER_USER_CONCURRENCY=2,
        ASYNC_JOB_RUNNING_TIMEOUT_SECONDS=2700,
        SERVICE_BUS_NAMESPACE_FQDN="unit-test.servicebus.windows.net",
        SERVICE_BUS_USE_CONNECTION_STRING=True,
        SERVICE_BUS_CONNECTION_STRING="Endpoint=sb://unit-test.servicebus.windows.net/;",
        SERVICE_BUS_AUTH_AUDIT_EXPORT_QUEUE_NAME="auth-audit-export",
        ASYNC_JOB_AUTH_AUDIT_EXPORT_TASK_NAME="jobs.auth_audit_export",
        SERVICE_BUS_SAMPLE_WAIT_BLOB_QUEUE_NAME="sample-wait-blob",
        ASYNC_JOB_SAMPLE_WAIT_BLOB_TASK_NAME="jobs.sample_wait_blob",
        AZURE_BLOB_ACCOUNT_URL="https://unit-test.blob.core.windows.net",
        AZURE_BLOB_CONTAINER="async-jobs",
        AZURE_BLOB_USE_CONNECTION_STRING=False,
        AZURE_BLOB_CONNECTION_STRING=None,
    )

    assert settings.async_jobs_enabled is False
    assert settings.async_job_max_rows_per_job == 1234
    assert settings.async_job_default_retention_days == 90
    assert settings.async_job_retention_max_days == 365
    assert settings.async_job_global_concurrency == 4
    assert settings.async_job_per_user_concurrency == 2
    assert settings.async_job_running_timeout_seconds == 2700
    assert settings.service_bus_namespace_fqdn == "unit-test.servicebus.windows.net"
    assert settings.service_bus_use_connection_string is True
    assert (
        settings.service_bus_connection_string
        == "Endpoint=sb://unit-test.servicebus.windows.net/;"
    )
    assert settings.auth_audit_export_queue_name == "auth-audit-export"
    assert settings.auth_audit_export_task_name == "jobs.auth_audit_export"
    assert settings.sample_wait_blob_queue_name == "sample-wait-blob"
    assert settings.sample_wait_blob_task_name == "jobs.sample_wait_blob"
    assert settings.azure_blob_account_url == "https://unit-test.blob.core.windows.net"
    assert settings.azure_blob_container == "async-jobs"
    assert settings.azure_blob_use_connection_string is False
    assert settings.azure_blob_connection_string is None
