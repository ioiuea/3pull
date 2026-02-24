"""
FastAPI アプリのブートストラップ.

- ライフサイクル管理を外部モジュール（lifespan）へ委譲する
- 構造化アクセスログ用ミドルウェアを組み込む
- API ルーターを公開プレフィックス配下に登録する
- 設定値は core.settings から読み込んで適用する
"""

from fastapi import FastAPI
import uvicorn

from app.api.routers.health import router as health_router
from app.core.lifecycle.startup import lifespan
from app.core.logging.middleware import AccessLogMiddleware
from app.core.settings.config import get_settings

SETTINGS = get_settings()
API_PREFIX = "/backend"

# アプリ生成時に lifecycle を紐づけ、起動/終了処理を一元管理する。
app = FastAPI(
    title=SETTINGS.service_name,
    version="v1",
    lifespan=lifespan,
)
# lifespan 側から参照する設定値を state に保持する。
app.state.api_prefix = API_PREFIX
# Uvicorn 標準アクセスログではなく、構造化ログミドルウェアを標準利用する。
app.add_middleware(AccessLogMiddleware)
# 公開 API ルーターをプレフィックス配下に集約する。
app.include_router(health_router, prefix=API_PREFIX)


def main() -> None:
    """
    開発用の起動エントリーポイント.

    `uv run backend` から呼び出されることを想定し、
    Uvicorn をリロード有効で起動する。
    """
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=SETTINGS.api_port,
        reload=True,
        access_log=False,
    )
