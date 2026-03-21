# core

`app.core` は、backend アプリケーション全体で共有する横断的な基盤機能をまとめるパッケージです。

業務機能そのものではなく、複数のレイヤーから参照される共通基盤をここに置きます。

## 含まれるもの

- `logging`
  - 構造化ログ設定とアクセスログ middleware
- `lifecycle`
  - FastAPI アプリの起動・終了処理
- `settings`
  - 環境変数ベースの設定スキーマと設定ロード
- `security`
  - HTTP 保護と認証用 crypto
- `datetime`
  - UTC 正規化などの日時ユーティリティ

## 含めないもの

- router 固有の request / response 処理
- 認証・監査・ジョブなどの業務ロジック
- repository や adapter の実装
- 特定機能専用の helper

## 利用方針

各サブパッケージは、それぞれの公開入口から import します。

```python
from app.core.logging import get_logger
from app.core.lifecycle import lifespan
from app.core.settings import get_settings
from app.core.security.http import require_current_user
from app.core.security.crypto import verify_password
from app.core.datetime import ensure_utc_datetime
```

`app.core` 自体は導線パッケージです。通常のアプリケーションコードでは、`app.core` 直下からまとめて import するのではなく、目的に応じたサブパッケージを使ってください。

## package guide

- [logging](./logging/README.md)
- [lifecycle](./lifecycle/README.md)
- [settings](./settings/README.md)
- [security](./security/README.md)
