"""
構造化アクセスログミドルウェア.

- すべての HTTP リクエスト/レスポンスを JSON で記録する
- 例外時は error ログとして詳細を出力する
"""

import time
from typing import Any

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class AccessLogMiddleware(BaseHTTPMiddleware):
    """各 HTTP リクエストのアクセスログを構造化出力する。"""

    def __init__(self, app: Any) -> None:
        """ミドルウェア初期化時に専用ロガーを準備する。"""
        super().__init__(app)
        self.logger = structlog.get_logger("app.access")

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        リクエスト処理時間を計測し、レスポンス結果をログ出力する.

        Args:
            request: 受信した HTTP リクエスト
            call_next: 次のハンドラーへ処理を委譲するコールバック
        """
        start_time = time.perf_counter()
        client_host = request.client.host if request.client else None
        request_id = request.headers.get("x-request-id")

        try:
            response = await call_next(request)
        except Exception:
            # 例外時も所要時間・リクエスト情報を必ず残す。
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self.logger.exception(
                "http.access.error",
                method=request.method,
                path=request.url.path,
                query=request.url.query,
                client=client_host,
                request_id=request_id,
                duration_ms=duration_ms,
            )
            raise

        # 正常レスポンス時のアクセスログ。
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        self.logger.info(
            "http.access",
            method=request.method,
            path=request.url.path,
            query=request.url.query,
            status_code=response.status_code,
            client=client_host,
            request_id=request_id,
            duration_ms=duration_ms,
        )
        return response
