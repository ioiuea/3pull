from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.api.routers.jobs.auth_audit_export import AuthAuditExportCreateRequest
from app.api.routers.jobs.sample_wait_blob import SampleWaitBlobCreateRequest


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
