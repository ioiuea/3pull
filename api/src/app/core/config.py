"""
アプリケーション設定

このモジュールは環境変数からアプリケーション設定を読み込みます。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    アプリケーション設定クラス

    環境変数または.envファイルから設定を読み込みます。

    Attributes:
        app_name: アプリケーション名
        app_env: アプリケーション環境（local/staging/production）
        app_timezone: アプリケーションのタイムゾーン
        debug: デバッグモードの有効/無効
        api_v1_prefix: API v1のURLプレフィックス
        host: サーバーのホスト
        port: サーバーのポート
        db_backend: データベースバックエンド（sqlite/cosmos）
        db_uri: データベース接続URI
        cosmos_uri: Azure Cosmos DB URI
        cosmos_key: Azure Cosmos DB アクセスキー
        cosmos_db_name: Azure Cosmos DB データベース名
        cosmos_container_folders: foldersコンテナ名
        cosmos_container_threads: chatThreadsコンテナ名
        fixed_user_id: 固定ユーザーID（認証実装まで使用）
        fixed_email: 固定メールアドレス（認証実装まで使用）
    """

    app_name: str = "FastAPI Backend"
    app_env: str = "local"
    app_timezone: str = "Asia/Tokyo"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    db_backend: str = "sqlite"
    db_uri: str = "sqlite+aiosqlite:///./data/app.db"

    cosmos_uri: str = ""
    cosmos_key: str = ""
    cosmos_db_name: str = "3pull"
    cosmos_container_folders: str = "folders"
    cosmos_container_threads: str = "chatThreads"

    fixed_user_id: str = "12345678-1234-1234-1234-123456789000"
    fixed_email: str = "test@3pull.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


def get_settings() -> Settings:
    """
    設定インスタンスを取得する

    Returns:
        Settings: アプリケーション設定インスタンス
    """
    return Settings()


settings = get_settings()
