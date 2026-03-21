"""backend の logging パッケージ.

- `config.py`
  - structlog の設定と logger 取得関数を提供する
- `middleware.py`
  - HTTP アクセスログミドルウェアを提供する

利用側は `app.core.logging` から
`get_logger` / `configure_logging` / `AccessLogMiddleware` を import する。
"""

from app.core.logging.config import configure_logging, get_logger
from app.core.logging.middleware import AccessLogMiddleware

__all__ = [
    "AccessLogMiddleware",
    "configure_logging",
    "get_logger",
]
