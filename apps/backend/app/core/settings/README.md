# core.settings

`core.settings` は、backend アプリケーションの設定値を環境変数から解決するためのパッケージです。

- `AppSettings`
  - 環境変数名と型、既定値、相関バリデーションを定義する設定スキーマです。
- `get_settings()`
  - `AppSettings` を LRU キャッシュ付きで返す公開入口です。

`config.py` は実装モジュールです。利用側は `app.core.settings` から import してください。

## Public API

```python
from app.core.settings import AppSettings, get_settings
```

## 利用方法

通常のアプリケーションコードでは、`get_settings()` を使って現在の設定を取得します。

```python
from app.core.settings import get_settings

settings = get_settings()

if settings.async_jobs_enabled:
    ...
```

FastAPI アプリ生成時に設定を一度解決して使う場合も、公開入口は同じです。

```python
from fastapi import FastAPI

from app.core.settings import get_settings

settings = get_settings()
app = FastAPI(title=settings.api_service_name)
```

テストや設定スキーマ自体の検証では、`AppSettings` を直接生成して使います。

```python
from app.core.settings import AppSettings

settings = AppSettings(
    ASYNC_JOBS_ENABLED=False,
    SERVICE_BUS_NAMESPACE_FQDN="unit-test.servicebus.windows.net",
)
```

## 役割の境界

- `core.settings` に置くもの
  - 環境変数の読み込み
  - 設定スキーマ
  - 設定値の型変換とバリデーション
- `core.settings` に置かないもの
  - ログ初期化
  - FastAPI middleware
  - 認証や暗号化の実装

## 実装メモ

- ローカル開発では `apps/backend/.env` が存在する場合のみ読み込みます。
- 実運用では環境変数注入を前提に動作します。
- `get_settings()` は `@lru_cache(maxsize=1)` でプロセス内共有インスタンスを返します。
