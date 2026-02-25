"""
Cookie セッション向け CSRF 防御ミドルウェア.

- 状態変更メソッドで Origin / Referer の送信元を検証する
- 信頼済みオリジンは AppSettings.csrf_trusted_origins で管理する
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    """Origin / Referer ヘッダーを用いた CSRF 防御."""

    _STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, app: Any, trusted_origins: list[str]) -> None:
        """
        ミドルウェアを初期化する.

        Args:
            app: ASGI アプリケーション
            trusted_origins: 許可するオリジン一覧（例: http://localhost:5173）
        """
        super().__init__(app)
        self._trusted_origins = {origin.rstrip("/") for origin in trusted_origins}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """
        状態変更リクエストの送信元を検証してから後続へ渡す.

        Args:
            request: 受信した HTTP リクエスト
            call_next: 次のハンドラーへ処理を委譲するコールバック

        Returns:
            Response: 検証結果に応じたレスポンス
        """
        method = request.method.upper()
        if method not in self._STATE_CHANGING_METHODS:
            return await call_next(request)

        origin = request.headers.get("origin")
        referer = request.headers.get("referer")

        if origin:
            if self._is_trusted_origin(origin):
                return await call_next(request)
            return self._reject("untrusted_origin")

        if referer:
            parsed = urlparse(referer)
            referer_origin = (
                f"{parsed.scheme}://{parsed.netloc}"
                if parsed.scheme and parsed.netloc
                else ""
            )
            if self._is_trusted_origin(referer_origin):
                return await call_next(request)
            return self._reject("untrusted_referer")

        return self._reject("missing_origin_and_referer")

    def _is_trusted_origin(self, origin: str) -> bool:
        """
        受信オリジンが許可リストに含まれるか判定する.

        Args:
            origin: 判定対象オリジン

        Returns:
            bool: 許可されている場合 True
        """
        return origin.rstrip("/") in self._trusted_origins

    @staticmethod
    def _reject(reason: str) -> JSONResponse:
        """
        CSRF 検証失敗レスポンスを返す.

        Args:
            reason: 失敗理由コード

        Returns:
            JSONResponse: 403 レスポンス
        """
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "CSRF validation failed", "reason": reason},
        )
