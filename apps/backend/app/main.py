"""
FastAPI アプリのブートストラップ.

- ライフサイクル管理を外部モジュール（lifespan）へ委譲する
- 構造化アクセスログ用ミドルウェアを組み込む
- API ルーターを公開プレフィックス配下に登録する
- 設定値は core.settings から読み込んで適用する
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routers.auth import router as auth_router
from app.api.routers.health import router as health_router
from app.core.lifecycle.startup import lifespan
from app.core.logging.middleware import AccessLogMiddleware
from app.core.security.csrf import CsrfProtectionMiddleware
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
# OIDC 認可フローの state / nonce を安全に保持するためセッションミドルウェアを追加する。
app.add_middleware(
    SessionMiddleware,
    secret_key=SETTINGS.session_secret_key,
    same_site="lax",
    https_only=SETTINGS.session_cookie_secure,
)
# Cookie セッション利用時の CSRF 対策として送信元オリジンを検証する。
app.add_middleware(
    CsrfProtectionMiddleware,
    trusted_origins=SETTINGS.csrf_trusted_origins,
)
# Uvicorn 標準アクセスログではなく、構造化ログミドルウェアを標準利用する。
app.add_middleware(AccessLogMiddleware)
# Frontend から Cookie 付きで API 呼び出しできるよう CORS を許可する。
app.add_middleware(
    CORSMiddleware,
    allow_origins=SETTINGS.csrf_trusted_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
# 公開 API ルーターをプレフィックス配下に集約する。
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
