"""
FastAPI 向けアプリ設定ローダ.

- pydantic-settings で環境変数を読み込む
- ローカル開発では apps/backend/.env が存在する場合のみ読み込む
- 本番では環境変数注入のみで動作する
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_dotenv_if_present(root_env_path: Path) -> None:
    """
    `.env` が存在する場合のみ dotenv を読み込む.

    python-dotenv 未導入または .env 不在時は何もせずに返す。

    Args:
        root_env_path: apps/backend/.env の絶対パス
    """
    if not root_env_path.exists():
        return

    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return

    # 既存の環境変数を優先し、dotenv で上書きしない。
    load_dotenv(dotenv_path=root_env_path, override=False)


# apps/backend/app/core/settings/config.py から 3 つ上が apps/backend/
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"
_load_dotenv_if_present(_ROOT_ENV)


class AppSettings(BaseSettings):
    """環境変数から解決されるアプリ設定。"""

    api_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        validation_alias="API_LOG_LEVEL",
    )

    service_name: str = Field(
        default="3pull-api",
        validation_alias="SERVICE_NAME",
    )

    api_port: int = Field(default=8000, validation_alias="API_PORT")

    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """LRU キャッシュで単一化した設定インスタンスを返す。"""
    return AppSettings()
