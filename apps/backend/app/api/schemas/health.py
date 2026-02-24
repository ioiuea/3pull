"""
ヘルスチェック API のスキーマ定義.

- ルーター層から返却するレスポンス構造を明示する
"""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス."""

    # ヘルスエンドポイントでは正常時に "ok" のみを返す。
    status: Literal["ok"]
