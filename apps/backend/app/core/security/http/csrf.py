"""Cookie セッション向け CSRF 防御ミドルウェア."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    """Origin / Referer ヘッダーを用いた CSRF 防御."""

    _STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, app: Any, trusted_origins: list[str]) -> None:
        super().__init__(app)
        self._trusted_origins = {origin.rstrip("/") for origin in trusted_origins}

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
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
        return origin.rstrip("/") in self._trusted_origins

    @staticmethod
    def _reject(reason: str) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "CSRF validation failed", "reason": reason},
        )


__all__ = ["CsrfProtectionMiddleware"]
