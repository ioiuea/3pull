# データベース初期化

このディレクトリには PostgreSQL の初期化スクリプトがあります。

## Azure Database for PostgreSQL Flexible Server 向け

これらのスクリプトは、標準的な `PG*` 環境変数で接続する前提です（Azure Flexible Server 互換）。  
新しい環境を作成した初回に一度実行してください。冪等に作られているため、再実行しても安全です。

### 各スクリプトの役割

- `apps/backend/postgres/run_all.sh`
  - 初期化スクリプトを順番にすべて実行します。

- `apps/backend/postgres/scripts/001_create_database.sh`
  - デフォルト DB `postgres` に接続し、`PGDATABASE` で指定した DB がなければ作成します。

- `apps/backend/postgres/scripts/002_create_schema.sh`
  - `PGDATABASE` に接続し、`core` スキーマを作成します（未作成時のみ）。

- `apps/backend/postgres/scripts/003_roles.sh`
  - API 用ロール（`core` スキーマ管理）を作成し、最小権限を付与し、`PUBLIC` 権限を制限します。

- `apps/backend/postgres/scripts/004_search_path.sh`
  - API 用ロールの `search_path` 既定値を設定します。
  - api 用: `core,public`

### 実行方法（プロジェクトルートで実行）

#### 0) 必要な環境変数を設定（シェルごとに1回）

```bash
export PGHOST=test-3pull-db.postgres.database.azure.com
export PGUSER=postgresadmin
export PGPORT=5432
export PGDATABASE=threepull
export PGPASSWORD="{your-password}"
export APP_DB_USER=threepull_api
```

#### 1) 初期化スクリプトを一括実行（通常はこちら）

```bash
bash apps/backend/postgres/run_all.sh
```

補足:
- `PGDATABASE` は新規作成するデータベース名です。
- DB 作成ステップではデフォルト DB `postgres` に接続して作成します。

#### 2) ステップごとに個別実行（必要時）

##### 2-1) データベース作成

```bash
bash apps/backend/postgres/scripts/001_create_database.sh
```

##### 2-2) スキーマ作成

```bash
bash apps/backend/postgres/scripts/002_create_schema.sh
```

##### 2-3) ロール作成・権限設定

```bash
bash apps/backend/postgres/scripts/003_roles.sh
```

##### 2-4) `search_path` 既定値設定

```bash
bash apps/backend/postgres/scripts/004_search_path.sh
```

データベース作成後のスキーマ変更は、`core` を Alembic で管理してください。
