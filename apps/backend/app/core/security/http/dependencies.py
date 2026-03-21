"""FastAPI dependency 向けの公開入口."""

from __future__ import annotations

from typing import Annotated, TypeAlias

from fastapi import Depends

from app.core.security.http.session import (
    AuthenticatedSessionContext,
    require_authenticated_session,
    require_current_user,
    require_session_context,
)
from app.models.auth.user import User

AuthenticatedSessionDep: TypeAlias = Annotated[
    AuthenticatedSessionContext,
    Depends(require_session_context),
]
CurrentUserDep: TypeAlias = Annotated[
    User,
    Depends(require_current_user),
]
AuthenticatedRequestDep: TypeAlias = Annotated[
    None,
    Depends(require_authenticated_session),
]

__all__ = [
    "AuthenticatedRequestDep",
    "AuthenticatedSessionDep",
    "CurrentUserDep",
    "require_authenticated_session",
    "require_current_user",
    "require_session_context",
]
