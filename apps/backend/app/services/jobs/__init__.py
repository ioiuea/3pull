"""非同期ジョブサービス."""

from app.services.jobs.async_job_dispatcher import dispatch_async_job

# 外からは「ジョブを投入する」入口だけを公開し、内部の送信実装を隠す。
__all__ = ["dispatch_async_job"]
