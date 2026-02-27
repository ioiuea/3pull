from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime


def batch_size_type(value: str) -> int:
    parsed = int(value)
    if not 100 <= parsed <= 50000:
        raise argparse.ArgumentTypeError("--batch-size must be between 100 and 50000")
    return parsed


def month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def add_months(dt: datetime, months: int) -> datetime:
    """
    月初日時に対する月単位の加減算.
    """
    absolute_month = (dt.year * 12 + (dt.month - 1)) + months
    year = absolute_month // 12
    month = (absolute_month % 12) + 1
    return dt.replace(year=year, month=month, day=1)


@dataclass(slots=True)
class CleanupResult:
    """cleanup 実行結果."""

    job_name: str
    status: str
    deleted_count: int
    duration_ms: float
    error: str | None = None
