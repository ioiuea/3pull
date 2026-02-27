from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException, status

from app.api.routers.jobs import _normalize_requested_payload, _resolve_task_binding
from app.models.jobs.async_job import AsyncJobType


def test_resolve_task_binding_for_audit_export() -> None:
    # 目的: 監査ログエクスポート種別が queue/task 設定へ正しく解決されることを保証する。
    # 条件: AUTH_AUDIT_EXPORT を入力する。
    # 期待値: queue_name/task_name が空でない文字列で返る。
    queue_name, task_name = _resolve_task_binding(AsyncJobType.AUTH_AUDIT_EXPORT)

    assert isinstance(queue_name, str)
    assert isinstance(task_name, str)
    assert queue_name != ""
    assert task_name != ""


def test_normalize_requested_payload_for_audit_export() -> None:
    # 目的: /jobs 作成時ペイロードが API 内部形式へ正規化されることを保証する。
    # 条件: event/provider/keyword/date range/timezone を含む入力を与える。
    # 期待値: requested_filters と timezone が欠落なく正規化される。
    payload = {
        "event_type": "auth.login.success",
        "provider": "email",
        "keyword": "alice@example.com",
        "date_from": datetime(2026, 2, 1, tzinfo=UTC).isoformat(),
        "date_to": datetime(2026, 2, 28, tzinfo=UTC).isoformat(),
        "timezone": "UTC",
    }

    normalized = _normalize_requested_payload(
        job_type=AsyncJobType.AUTH_AUDIT_EXPORT,
        payload=payload,
    )

    assert normalized["timezone"] == "UTC"
    assert normalized["requested_filters"]["event_type"] == "auth.login.success"
    assert normalized["requested_filters"]["provider"] == "email"
    assert normalized["requested_filters"]["keyword"] == "alice@example.com"
    assert normalized["requested_filters"]["date_from"] is not None
    assert normalized["requested_filters"]["date_to"] is not None


def test_normalize_requested_payload_rejects_invalid_timezone() -> None:
    # 目的: timezone の型不正を早期に検知して不正入力を防ぐ。
    # 条件: timezone に文字列以外（数値）を渡す。
    # 期待値: 例外が送出される。
    payload = {
        "timezone": 1234,
    }
    with pytest.raises(Exception):
        _normalize_requested_payload(
            job_type=AsyncJobType.AUTH_AUDIT_EXPORT,
            payload=payload,
        )


def test_resolve_task_binding_rejects_unsupported_job_type() -> None:
    # 目的: 未対応 job_type が API で明示的に拒否されることを固定する。
    # 条件: 未対応の擬似 job_type を渡す。
    # 期待値: 422 / unsupported_job_type を返す。
    class _UnsupportedType:
        value = "unsupported"

    with pytest.raises(HTTPException) as exc:
        _resolve_task_binding(_UnsupportedType())  # type: ignore[arg-type]

    assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert exc.value.detail["code"] == "unsupported_job_type"
