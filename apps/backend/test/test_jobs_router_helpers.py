from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.jobs.create.auth_audit_export import AuthAuditExportCreateRequest
from app.api.routers.jobs.helpers import (
    enforce_async_job_concurrency,
    ensure_async_jobs_enabled,
    resolve_async_job_expiration,
)
from app.models.jobs.async_job import AsyncJobType
from app.api.routers.jobs.create.sample_wait_blob import SampleWaitBlobCreateRequest


def test_auth_audit_export_request_model_accepts_payload() -> None:
    # 目的: 監査ログエクスポート作成エンドポイントの入力モデルが
    # 期待フィールドを受理することを保証する。
    # 条件: event/provider/keyword/date range/timezone を含む入力を与える。
    # 期待値: 入力値がモデル上で保持される。
    model = AuthAuditExportCreateRequest(
        event_type="auth.login.success",
        provider="email",
        keyword="alice@example.com",
        date_from=datetime(2026, 2, 1, tzinfo=UTC).isoformat(),
        date_to=datetime(2026, 2, 28, tzinfo=UTC).isoformat(),
        timezone="UTC",
    )

    assert model.event_type is not None
    assert model.provider == "email"
    assert model.keyword == "alice@example.com"
    assert model.date_from is not None
    assert model.date_to is not None
    assert model.timezone == "UTC"


def test_sample_wait_blob_request_model_accepts_payload() -> None:
    # 目的: サンプル待機ジョブ作成エンドポイントの入力モデルが
    # 期待フィールドを受理することを保証する。
    # 条件: wait_seconds / content を含む入力を与える。
    # 期待値: 入力値がモデル上で保持される。
    model = SampleWaitBlobCreateRequest(
        wait_seconds=120,
        content="hello",
    )

    assert model.wait_seconds == 120
    assert model.content == "hello"


def test_auth_audit_export_request_model_rejects_invalid_timezone_type() -> None:
    # 目的: 監査ログエクスポート入力モデルで timezone 型不正が弾かれることを保証する。
    # 条件: timezone に文字列以外（数値）を渡す。
    # 期待値: バリデーションエラーが送出される。
    with pytest.raises(Exception):
        AuthAuditExportCreateRequest(timezone=1234)


def test_ensure_async_jobs_enabled_raises_when_disabled(monkeypatch) -> None:
    # 目的: 非同期ジョブ機能が無効な場合に API 共通ガードが 404 を返すことを保証する。
    # 条件: settings.async_jobs_enabled を False に差し替える。
    # 期待値: jobs_feature_disabled コードで HTTPException が送出される。
    settings = type("Settings", (), {"async_jobs_enabled": False})()
    monkeypatch.setattr("app.api.routers.jobs.helpers.get_settings", lambda: settings)

    with pytest.raises(HTTPException) as exc_info:
        ensure_async_jobs_enabled()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["code"] == "jobs_feature_disabled"


def test_resolve_async_job_expiration_clamps_retention_days(monkeypatch) -> None:
    # 目的: 保持日数が上限を超える場合でも API 共通ヘルパーで補正されることを保証する。
    # 条件: default=7, max=30 の設定で retention_days=60 を渡す。
    # 期待値: 返る expires_at は現在時刻から約 30 日後になる。
    settings = type(
        "Settings",
        (),
        {
            "async_job_default_retention_days": 7,
            "async_job_retention_max_days": 30,
        },
    )()
    monkeypatch.setattr("app.api.routers.jobs.helpers.get_settings", lambda: settings)

    now = datetime.now(UTC)
    expires_at = resolve_async_job_expiration(retention_days=60)

    assert now + timedelta(days=29, hours=23) < expires_at
    assert expires_at < now + timedelta(days=30, minutes=1)


@pytest.mark.asyncio
async def test_enforce_async_job_concurrency_scopes_counts_by_job_type(
    monkeypatch,
) -> None:
    # 目的: 同時実行チェックが job_type ごとの件数だけを数えることを保証する。
    # 条件: count 関数を差し替え、呼び出し時の job_type 引数を記録する。
    # 期待値: global / user の両方で指定 job_type が渡される。
    settings = type(
        "Settings",
        (),
        {
            "async_job_global_concurrency": 10,
            "async_job_per_user_concurrency": 10,
        },
    )()
    captured: dict[str, object] = {}

    async def _fake_count_active_async_jobs(
        session: AsyncSession,
        *,
        job_type: AsyncJobType | None = None,
    ) -> int:
        captured["global_job_type"] = job_type
        return 0

    async def _fake_count_active_async_jobs_by_user(
        session: AsyncSession,
        *,
        requested_by_user_id: str,
        job_type: AsyncJobType | None = None,
    ) -> int:
        captured["user_job_type"] = job_type
        return 0

    monkeypatch.setattr("app.api.routers.jobs.helpers.get_settings", lambda: settings)
    monkeypatch.setattr(
        "app.api.routers.jobs.helpers.count_active_async_jobs",
        _fake_count_active_async_jobs,
    )
    monkeypatch.setattr(
        "app.api.routers.jobs.helpers.count_active_async_jobs_by_user",
        _fake_count_active_async_jobs_by_user,
    )

    await enforce_async_job_concurrency(
        session=object(),
        requested_by_user_id="user-1",
        job_type=AsyncJobType.AUTH_AUDIT_EXPORT,
    )

    assert captured["global_job_type"] == AsyncJobType.AUTH_AUDIT_EXPORT
    assert captured["user_job_type"] == AsyncJobType.AUTH_AUDIT_EXPORT
