"""
ヘルスチェック API のルーター定義.

- `/health` エンドポイントを公開する
- レスポンスは `schemas.health.HealthResponse` で型定義する
"""

from fastapi import APIRouter

from app.api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """サービスの稼働状態を返す。"""
    return HealthResponse(status="ok")
