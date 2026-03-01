"""非同期ジョブリポジトリ."""

from app.repositories.jobs.async_job_artifact_repository import (
    count_async_job_artifacts_by_job_id,
    count_expired_async_job_artifacts,
    create_async_job_artifact,
    delete_async_job_artifacts_by_ids,
    get_async_job_artifact_by_id,
    get_latest_async_job_artifact,
    list_async_job_artifacts_by_job,
    list_expired_async_job_artifacts,
)
from app.repositories.jobs.async_job_repository import (
    claim_queued_job_for_run,
    count_active_async_jobs,
    count_active_async_jobs_by_user,
    count_stale_running_async_jobs,
    create_async_job,
    get_async_job_by_id,
    list_async_jobs_by_user,
    list_stale_running_async_jobs,
    mark_async_jobs_expired_by_ids,
    mark_async_jobs_failed_by_ids,
    update_async_job_status,
)

__all__ = [
    "create_async_job",
    "claim_queued_job_for_run",
    "get_async_job_by_id",
    "list_async_jobs_by_user",
    "count_active_async_jobs",
    "count_active_async_jobs_by_user",
    "count_stale_running_async_jobs",
    "update_async_job_status",
    "create_async_job_artifact",
    "count_expired_async_job_artifacts",
    "list_expired_async_job_artifacts",
    "delete_async_job_artifacts_by_ids",
    "count_async_job_artifacts_by_job_id",
    "get_async_job_artifact_by_id",
    "get_latest_async_job_artifact",
    "list_async_job_artifacts_by_job",
    "list_stale_running_async_jobs",
    "mark_async_jobs_failed_by_ids",
    "mark_async_jobs_expired_by_ids",
]
