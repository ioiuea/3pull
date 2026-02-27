"""
Celery アプリ初期化アダプタ.
"""

from __future__ import annotations

from functools import lru_cache

from celery import Celery
from redis import Redis

from app.core.settings import get_settings

_PUBLISH_RETRY_POLICY = {
    "max_retries": 3,
    "interval_start": 0,
    "interval_step": 0.2,
    "interval_max": 1.0,
}


def _resolve_result_backend_url() -> str:
    """
    Celery result backend URL を解決する.

    - CELERY_RESULT_BACKEND_URL 優先
    - 未設定時は CELERY_BROKER_URL を再利用
    """
    settings = get_settings()
    if settings.celery_result_backend_url:
        return settings.celery_result_backend_url
    if settings.celery_broker_url:
        return settings.celery_broker_url
    raise RuntimeError("CELERY_BROKER_URL is required to initialize Celery")


@lru_cache(maxsize=1)
def get_celery_app() -> Celery:
    """
    汎用ジョブ実行向け Celery アプリを返す.
    """
    settings = get_settings()
    if not settings.celery_broker_url:
        raise RuntimeError("CELERY_BROKER_URL is required to initialize Celery")

    celery_app = Celery(
        "app_tasks",
        broker=settings.celery_broker_url,
        backend=_resolve_result_backend_url(),
        include=settings.celery_task_modules,
    )

    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        broker_connection_retry_on_startup=True,
        task_publish_retry=True,
        task_publish_retry_policy=_PUBLISH_RETRY_POLICY,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_track_started=True,
        task_time_limit=settings.celery_task_time_limit_seconds,
    )
    return celery_app


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    """
    broker URL を使って Redis クライアントを返す.
    """
    settings = get_settings()
    if not settings.celery_broker_url:
        raise RuntimeError("CELERY_BROKER_URL is required to initialize Redis client")
    return Redis.from_url(settings.celery_broker_url)


def ping_redis() -> bool:
    """
    Redis へ疎通確認を行う.
    """
    return bool(get_redis_client().ping())
