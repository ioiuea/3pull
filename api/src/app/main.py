"""
FastAPIアプリケーション

このモジュールはFastAPIアプリケーションのエントリーポイントです。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.v1.router import get_v1_router


def create_application() -> FastAPI:
    """
    FastAPIアプリケーションを作成

    Returns:
        FastAPI: FastAPIアプリケーションインスタンス
    """
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    v1_router = get_v1_router()
    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    return app


app = create_application()


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """
    ルートエンドポイント

    Returns:
        dict[str, str]: ウェルカムメッセージ
    """
    return {"message": f"{settings.app_name}へようこそ", "docs": "/docs"}
