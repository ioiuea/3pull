"""
SQLAlchemy の Declarative Base 定義.

- Alembic autogenerate で安定した差分検出を行うため命名規約を統一する
- すべての ORM モデルが継承する Base を提供する
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """全 ORM モデルが継承する Declarative Base."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
