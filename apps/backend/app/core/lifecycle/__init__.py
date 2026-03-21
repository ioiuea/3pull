"""backend のライフサイクル管理パッケージ.

- `startup.py`
  - FastAPI の lifespan を定義する
  - 起動時の初期化と停止時の後処理を管理する

利用側は `app.core.lifecycle` から `lifespan` を import する。
"""

from app.core.lifecycle.startup import lifespan

__all__ = ["lifespan"]
