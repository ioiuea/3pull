from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models.auth.auth_audit_log import AuthAuditEventType
from app.workers.audit_export_tasks import (
    PermanentExportError,
    _build_blob_path,
    _extract_filters,
    _parse_datetime_value,
    _resolve_timezone,
)


def test_parse_datetime_value_accepts_iso_string() -> None:
    # 目的: ISO8601 文字列が timezone 付き datetime に解釈されることを保証する。
    # 条件: UTC offset を含む文字列を渡す。
    # 期待値: tzinfo ありの datetime が返る。
    parsed = _parse_datetime_value("2026-02-27T10:00:00+00:00")
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.isoformat() == "2026-02-27T10:00:00+00:00"


def test_extract_filters_parses_event_type_and_dates() -> None:
    # 目的: requested_filters の各入力が
    # worker 用フィルタに正しく変換されることを保証する。
    # 条件: event_type/provider/keyword/date_from/date_to を与える。
    # 期待値: event_type enum 化、文字列 trim、日時パースが行われる。
    event_type, provider, keyword, date_from, date_to = _extract_filters(
        {
            "event_type": AuthAuditEventType.LOGIN_SUCCESS.value,
            "provider": " email ",
            "keyword": " alice ",
            "date_from": "2026-02-01T00:00:00+00:00",
            "date_to": "2026-02-28T23:59:59+00:00",
        }
    )

    assert event_type == AuthAuditEventType.LOGIN_SUCCESS
    assert provider == "email"
    assert keyword == "alice"
    assert date_from is not None
    assert date_to is not None


def test_extract_filters_rejects_invalid_event_type() -> None:
    # 目的: 未定義 event_type を拒否して誤った抽出を防ぐ。
    # 条件: enum に存在しない event_type を渡す。
    # 期待値: PermanentExportError が送出される。
    with pytest.raises(PermanentExportError):
        _extract_filters({"event_type": "invalid.event"})


def test_resolve_timezone_rejects_non_allowlist() -> None:
    # 目的: allowlist 外 timezone の使用を防ぐ。
    # 条件: 許可されていない timezone を指定する。
    # 期待値: PermanentExportError が送出される。
    with pytest.raises(PermanentExportError):
        _resolve_timezone("Asia/Seoul")


def test_build_blob_path_uses_expected_prefix() -> None:
    # 目的: 成果物の Blob パス命名規約（prefix/year/month/job_id）を固定する。
    # 条件: 固定日時と job_id でパス生成する。
    # 期待値: audit-exports/YYYY/MM/{job_id}.csv になる。
    path = _build_blob_path(
        now_utc=datetime(2026, 2, 27, 0, 0, 0, tzinfo=UTC),
        job_id="job-xyz",
    )

    assert path == "audit-exports/2026/02/job-xyz.csv"
