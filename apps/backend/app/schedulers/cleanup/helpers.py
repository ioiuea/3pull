"""cleanup CLI と各 cleanup 処理で共通利用する補助定義."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime


def batch_size_type(value: str) -> int:
    # CLI 入力の段階で batch_size を絞り、極端な値を早めに弾く。
    parsed = int(value)
    if not 100 <= parsed <= 50000:
        raise argparse.ArgumentTypeError("--batch-size must be between 100 and 50000")
    return parsed


def month_start(dt: datetime) -> datetime:
    # パーティション管理では「月初」を基準に扱うため、時刻も含めて月初へ丸める。
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def add_months(dt: datetime, months: int) -> datetime:
    """
    月初日時に対する月単位の加減算.
    """
    # 日単位の timedelta では月末長の違いを安全に扱いにくいため、
    # 月番号を絶対値で計算してから year/month へ戻している。
    absolute_month = (dt.year * 12 + (dt.month - 1)) + months
    year = absolute_month // 12
    month = (absolute_month % 12) + 1
    return dt.replace(year=year, month=month, day=1)


@dataclass(slots=True)
class CleanupResult:
    """cleanup 実行結果."""

    # runner 側はこの共通 shape だけを見てログと終了コードを扱う。
    job_name: str
    status: str
    deleted_count: int
    duration_ms: float
    error: str | None = None
