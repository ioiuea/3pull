"""
pyodbc を用いた Azure SQL 向け SQLAlchemy エンジン / セッション定義.

- DATABASE_URL（例: `mssql+pyodbc://@server.database.windows.net/db?...`）を使用する
- Microsoft Entra アクセストークンを ODBC 接続属性へ注入する
- Alembic / backend 本体の共通接続土台を提供する
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import cast

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.adapters.sql.token import (
    SQL_COPT_SS_ACCESS_TOKEN,
    create_access_token_struct,
)
from app.core.settings import get_settings

logger = logging.getLogger(__name__)
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _sanitize_odbc_connect_string(connect_string: str) -> str:
    """
    Microsoft Entra アクセストークン接続と競合する ODBC オプションを除去する.

    SQLAlchemy の mssql+pyodbc URL では、条件によって `Trusted_Connection=Yes`
    が自動付与されることがあり、アクセストークン接続と同時利用できない。
    """
    blocked_prefixes = (
        "trusted_connection=",
        "authentication=",
        "integrated security=",
        "uid=",
        "user id=",
        "pwd=",
        "password=",
    )
    sanitized_parts: list[str] = []
    for part in connect_string.split(";"):
        stripped = part.strip()
        if not stripped:
            continue
        if stripped.lower().startswith(blocked_prefixes):
            continue
        sanitized_parts.append(stripped)
    return ";".join(sanitized_parts)


def resolve_database_url() -> str:
    """
    DATABASE_URL を解決し、未設定時は明示的に失敗させる.

    Returns:
        str: SQLAlchemy 用 DATABASE_URL

    Raises:
        RuntimeError: DATABASE_URL が未設定の場合
    """
    settings = get_settings()
    database_url = settings.database_url
    if not database_url:
        logger.error("DATABASE_URL is not set for Azure SQL connection")
        raise RuntimeError("DATABASE_URL is not set")
    return database_url


def _install_access_token_hook(engine: Engine) -> None:
    """
    pyodbc 接続時に Microsoft Entra アクセストークンを注入する.
    """
    settings = get_settings()

    def _provide_token(
        dialect: object,
        conn_rec: object,
        cargs: list[object],
        cparams: dict[str, object],
    ) -> None:
        del dialect, conn_rec

        if cargs and isinstance(cargs[0], str):
            cargs[0] = _sanitize_odbc_connect_string(cargs[0])

        raw_attrs_before = cparams.get("attrs_before")
        attrs_before = (
            cast(dict[int, bytes], raw_attrs_before)
            if isinstance(raw_attrs_before, dict)
            else {}
        )
        attrs_before[SQL_COPT_SS_ACCESS_TOKEN] = create_access_token_struct(
            scope=settings.database_access_token_scope
        )
        cparams["attrs_before"] = attrs_before

    event.listen(engine, "do_connect", _provide_token)


def build_sync_engine(*, use_null_pool: bool = False) -> Engine:
    """
    Azure SQL 向け同期 Engine を構築する.

    Args:
        use_null_pool: Alembic 用に NullPool を使う場合に `True`

    Returns:
        Engine: SQLAlchemy 同期 Engine
    """
    settings = get_settings()
    engine_kwargs: dict[str, object] = {
        "echo": settings.database_echo,
        "pool_pre_ping": True,
    }
    if use_null_pool:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = settings.database_pool_size
        engine_kwargs["max_overflow"] = settings.database_max_overflow
        engine_kwargs["pool_timeout"] = settings.database_pool_timeout

    engine = create_engine(
        resolve_database_url(),
        **engine_kwargs,
    )
    _install_access_token_hook(engine)
    return engine


def get_engine() -> Engine:
    """共有同期 Engine を返す。"""
    global _engine
    if _engine is None:
        _engine = build_sync_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """同期セッションファクトリを返す。"""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            class_=Session,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


def get_session() -> Iterator[Session]:
    """
    トランザクション境界付きの同期 Session を yield する.
    """
    session_factory = get_session_factory()
    with session_factory.begin() as session:
        yield session


def dispose_engine() -> None:
    """アプリ停止時にエンジン接続プールを解放する。"""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
