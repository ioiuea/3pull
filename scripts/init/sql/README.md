# SQL Database Init Scripts

このディレクトリには、Azure SQL Database の初期設定で一度だけ実行する補助スクリプトを配置します。

現時点の目的:

- `auth` スキーマの作成
- `audit` スキーマの作成
- `core` スキーマの作成

含まれるファイル:

- `deploy.sh`
  - `auth` / `audit` / `core` スキーマを存在しない場合のみ作成します。
  - `az login` 中の自分の Entra アカウントを Azure SQL Database ユーザーとして作成し、各スキーマへの権限を付与します。
  - Azure SQL への接続は `az account get-access-token` で取得した access token と `pyodbc` を使います。

実行方法の例:

- `deploy.sh`

`deploy.sh` の例:

```bash
./scripts/init/sql/deploy.sh
```

ローカル向けに対話で DB 名を入れたい場合:

```bash
./scripts/init/sql/deploy.sh -local
```

注意:

- 現在の Alembic migration / SQLAlchemy model は `auth` / `audit` / `core` スキーマ前提です。
- 既存 DB を `dbo` 前提 migration で一度作成済みの場合は、テーブルと `alembic_version` をいったんリセットしてから新しい initial migration を適用してください。
- `deploy.sh` は `az ad signed-in-user show --query userPrincipalName -o tsv` を優先し、取得できない場合のみ `az account show --query user.name -o tsv` をフォールバックとして使います。
- `deploy.sh` は `uv --directory apps/backend run python` を優先して使います。事前に `apps/backend` の依存が入っていることを前提にしています。
- `deploy.sh` を実行するアカウントは、対象 Azure SQL Database 上で `CREATE USER` と権限付与を行える権限を持っている必要があります。
