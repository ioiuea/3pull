"""
ヘルスチェックエンドポイント

このモジュールはアプリケーションのヘルスチェック機能を提供します。
"""

from fastapi import APIRouter

from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """
    ヘルスチェック

    アプリケーションが正常に動作しているかを確認します。

    Returns:
        HealthResponse: ヘルスチェック結果

    Examples:
        >>> response = await health_check()
        >>> response.status
        'healthy'
    """
    return HealthResponse(
        status="healthy", message="アプリケーションは正常に動作しています"
    )
