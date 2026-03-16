"""
日時ユーティリティ.
"""

from __future__ import annotations

from datetime import datetime, timezone


def ensure_utc_datetime(value: datetime | None) -> datetime | None:
    """DB 由来の datetime を UTC aware に正規化する."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
