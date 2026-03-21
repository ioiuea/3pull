"""
ヘルスチェック API のスキーマ定義.

- ルーター層から返却するレスポンス構造を明示する
"""

from typing import Literal

from pydantic import BaseModel


class TcpDependencyHealth(BaseModel):
    """TCP 到達性チェック結果."""

    host: str
    port: int
    ok: bool
    latency_ms: int
    error: str | None = None


class HealthDependencies(BaseModel):
    """依存先サービスごとの健全性."""

    sql: TcpDependencyHealth
    redis: TcpDependencyHealth
    service_bus: TcpDependencyHealth
    storage: TcpDependencyHealth


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス."""

    # 依存先が全て到達可能なら ok、どれか失敗なら degraded。
    status: Literal["ok", "degraded"]
    dependencies: HealthDependencies
