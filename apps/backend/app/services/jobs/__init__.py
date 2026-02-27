"""非同期ジョブサービス."""

from app.services.jobs.async_job_dispatcher import dispatch_async_job

__all__ = ["dispatch_async_job"]
