"""
日時ユーティリティ

このモジュールは日時の生成と変換機能を提供します。
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def utc_now() -> datetime:
    """
    現在のUTC日時を取得する

    Returns:
        datetime: タイムゾーン付きUTC datetime

    Example:
        ```python
        now = utc_now()
        print(now)  # 2025-10-16 05:30:00+00:00
        ```
    """
    return datetime.now(UTC)


def to_api_datetime(dt_utc: datetime) -> str:
    """
    UTC datetimeをAPI出力用のISO8601文字列に変換する

    APP_TIMEZONEで指定されたタイムゾーンに変換し、
    ISO8601形式（YYYY-MM-DDTHH:mm:ss±HH:MM）の文字列を返します。

    Args:
        dt_utc: UTC datetime

    Returns:
        str: ISO8601形式のタイムゾーン付き文字列

    Example:
        ```python
        now = utc_now()
        api_str = to_api_datetime(now)
        print(api_str)  # "2025-10-16T14:30:00+09:00"
        ```
    """
    tz = ZoneInfo(settings.app_timezone)
    dt_local = dt_utc.astimezone(tz)
    return dt_local.isoformat()
