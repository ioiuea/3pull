# SQL Database Init Scripts

このディレクトリには、Azure SQL Database の初期設定で一度だけ実行する補助スクリプトを配置します。

目的:

- `auth` スキーマの作成
- `audit` スキーマの作成
- `core` スキーマの作成
- Azure SQL Database 内 principal の作成
- schema 権限付与

含まれるファイル:

- `deploy.sh`
  - `--local` 付き:
    - `auth` / `audit` / `core` スキーマを存在しない場合のみ作成します。
    - `az login` 中の個人 Entra principal を Azure SQL Database ユーザーとして作成し、各スキーマへの権限を付与します。
    - 接続先 DB 名 / SQL Server FQDN を対話入力で受け取ります。
  - `--local` なし:
    - `param.conf` を読み込みます。
    - `SQL_ADMIN_LOGIN` を使って SQL 認証で接続し、パスワードは対話入力で受け取ります。
    - API / worker / schedulers / migration 用 Managed Identity principal を Azure SQL Database ユーザーとして作成し、設計済みの schema 権限を付与します。
  - `--local` は `az account get-access-token` + `pyodbc`、通常モードは SQL 認証 + `pyodbc` を使います。
- `param.conf`
  - `infra/main.sh` が動的生成する設定ファイルです。
  - SQL Server FQDN、データベース名、SQL admin login、Managed Identity 名を保持します。
  - Git 管理対象外です。

実行例:

bootstrap 用（maint-vm など、generated `param.conf` を利用）:

```bash
./scripts/init/sql/deploy.sh
```

ローカル向けに対話で DB 名を入れたい場合:

```bash
./scripts/init/sql/deploy.sh --local
```

注意:

- 現在の Alembic migration / SQLAlchemy model は `auth` / `audit` / `core` スキーマ前提です。
- 既存 DB を `dbo` 前提 migration で一度作成済みの場合は、テーブルと `alembic_version` をいったんリセットしてから新しい initial migration を適用してください。
- `deploy.sh --local` は `az ad signed-in-user show --query userPrincipalName -o tsv` を優先し、取得できない場合のみ `az account show --query user.name -o tsv` をフォールバックとして使います。
- `deploy.sh` は `uv --directory apps/backend run python` を優先して使います。事前に `apps/backend` の依存が入っていることを前提にしています。
- 通常モードでは、`param.conf` の `SQL_ADMIN_LOGIN` で接続し、SQL admin password を対話入力します。
- `--local` を実行する principal は、対象 Azure SQL Database 上で `CREATE USER` と権限付与を行える権限を持っている必要があります。
- `param.conf` は `infra/main.sh` 実行時に `scripts/init/sql/param.conf` へ上書き生成されます。
