"""
アプリ設定パッケージ.

- `AppSettings` で環境変数ベースの設定スキーマを提供する
- `get_settings()` でプロセス内共有の設定インスタンスを返す
- 利用側は `app.core.settings` から import し、`config.py` を直接参照しない
"""

from app.core.settings.config import AppSettings, get_settings

__all__ = ["AppSettings", "get_settings"]
