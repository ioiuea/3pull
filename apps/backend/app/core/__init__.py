"""
アプリケーション横断の基盤機能をまとめるパッケージ.

- `logging`
  - 構造化ログ設定とアクセスログ middleware を提供する
- `lifecycle`
  - FastAPI アプリの起動・終了処理を提供する
- `settings`
  - 環境変数ベースの設定スキーマと設定ロードを提供する
- `telemetry`
  - Azure Monitor OpenTelemetry の初期化を提供する
- `security`
  - HTTP 保護と認証用 crypto を提供する
- `datetime`
  - UTC 正規化などの日時ユーティリティを提供する

`core` には、特定の業務機能に閉じない横断的な基盤機能を置く。
router 固有の処理、認証業務ロジック、DB repository などは `core` に置かない。
"""
