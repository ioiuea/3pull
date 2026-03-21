"""security middleware の組み込み入口."""

from fastapi import FastAPI

from app.core.security.http.csrf import CsrfProtectionMiddleware
from app.core.settings import get_settings


def install_security_middleware(app: FastAPI) -> None:
    """HTTP security middleware をアプリへ組み込む."""
    settings = get_settings()
    app.add_middleware(
        CsrfProtectionMiddleware,
        trusted_origins=settings.csrf_trusted_origins,
    )
