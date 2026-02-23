# AGENTS

## Package Manager Policy

- `apps/backend` のパッケージ管理は `uv` を標準とします。
- 依存追加・更新・同期は `uv add` / `uv remove` / `uv sync` を利用します。
- ロックファイルは `uv.lock` を正とし、チーム開発では lockfile ベースで再現可能な環境を維持します。

## API Framework Policy

- API フレームワークは `FastAPI` を標準採用します。
- エントリーポイントは `apps/backend/app/main.py` とし、`app = FastAPI()` をこのファイルで管理します。
- ルーティング、依存性注入、ミドルウェアなどの API 構成は FastAPI の標準機能を優先して実装します。

## `app/__init__.py` Policy

- `apps/backend/app/__init__.py` は、`app` ディレクトリを Python パッケージとして扱うために配置します。
- 現時点では公開 API の集約は行わないため、`__init__.py` は原則空ファイルで維持します。
- 将来、パッケージ公開面の都合で再エクスポートが必要になった場合のみ、`__init__.py` に `__all__` や公開シンボルを明示的に追加します。
- 実行ロジックや副作用のある初期化処理は `__init__.py` に書かず、`app/main.py` または適切なモジュールへ配置します。
