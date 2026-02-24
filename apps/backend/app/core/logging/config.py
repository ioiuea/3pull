"""
structlog の設定モジュール.

- アプリ全体の構造化ログ設定を一元管理する
- logger 取得関数を提供して利用箇所を統一する
"""

import logging

import structlog


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    structlog ベースのロガーを返す.

    Args:
        name: ロガー名。未指定時はデフォルトロガーを返す。
    """
    return structlog.get_logger(name)


def configure_logging(level: str = "INFO") -> None:
    """
    アプリケーションの構造化ログを初期化する.

    - 時刻・ログレベル・ロガー名を付与
    - 例外情報を整形
    - 最終的に JSON 形式で出力
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # stdlib logging からの出力形式も structlog に合わせる。
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
    )
