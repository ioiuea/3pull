# Maint VM Setup

Ubuntu で、以下を実行できる状態にするためのセットアップ手順をまとめる。

- `scripts/init/sql/deploy.sh`
- `make alembic-upgrade`

前提:

- VM イメージは Ubuntu 24.04 LTSだとする
- このリポジトリを VM 上に clone 済み
- Azure SQL へのネットワーク疎通は確保済み
- migration 用 User Assigned Managed Identity は VM に割り当て済み

## インストール対象

### DB bootstrap / Alembic 実行に必要な OS パッケージ

- `git`
- `make`
- `apt-transport-https`
- `python-is-python3`
- `python3.12`
- `python3.12-venv`
- `curl`
- `ca-certificates`
- `gnupg`
- `lsb-release`
- `unixodbc`
- `unixodbc-dev`
- `msodbcsql18`
- `azure-cli`

### DB bootstrap / Alembic 実行に必要なユーザー領域インストール

- `uv`

### DB bootstrap / Alembic 実行に必要な Python 依存

- `pyodbc`
  - `apps/backend` で `uv sync --frozen` を実行して導入する

### AKS 運用を行う場合に追加で必要なツール

- `kubectl`
- `helm`
- `kubelogin`

## 役割

- `git`: このリポジトリを VM 上に clone / pull するために必要
- `make`: `make alembic-upgrade` の実行に必要
- `apt-transport-https`: APT で HTTPS リポジトリを扱うために必要
- `python-is-python3`: `python` コマンドを `python3` に向けるために必要
- `python3.12`: backend / Alembic / `deploy.sh` の Python 実行基盤として必要
- `python3.12-venv`: Python 仮想環境を扱うために必要になる場合があるため導入
- `curl`: `msodbcsql18` 用の Microsoft repo 登録、`azure-cli` インストーラ、`uv` インストーラ取得に必要
- `ca-certificates`: `curl` で HTTPS 経由の installer や package repo に安全に接続するために必要
- `gnupg`: APT の外部リポジトリ鍵や署名検証で必要になる場合があるため導入
- `lsb-release`: Ubuntu の distribution codename を取得し、APT repo 設定に使う
- `uv`: backend の Python 依存導入と Alembic 実行に必要
- `unixodbc`: Linux の ODBC マネージャとして必要。`pyodbc` と ODBC ドライバの仲介を行う
- `unixodbc-dev`: `pyodbc` のビルドやヘッダ解決で必要になる場合があるため導入
- `msodbcsql18`: Azure SQL / SQL Server 向け ODBC ドライバ本体として必要。実際に SQL Server プロトコルで通信する
- `azure-cli`: Managed Identity ログイン確認や Azure 運用コマンド実行に必要
- `kubectl`: AKS に対する Kubernetes API 操作用に必要
- `helm`: AKS 上のアプリ / chart デプロイ用に必要
- `kubelogin`: Azure RBAC/AAD ベースの kubeconfig を `kubectl` から使うために必要
- `pyodbc`: Python から ODBC 経由で Azure SQL に接続するために必要

## 手順

### 1. APT パッケージ索引を更新する

```bash
sudo apt-get update
```

### 2. 基本パッケージを入れる

```bash
sudo apt-get install -y \
  git \
  make \
  apt-transport-https \
  python-is-python3 \
  python3.12 \
  python3.12-venv \
  curl \
  ca-certificates \
  gnupg \
  lsb-release \
  unixodbc \
  unixodbc-dev
```

補足:

- Ubuntu 24.04 では `python3.12` は標準系だが、明示的に入れておく。
- Ubuntu では `python3` はあっても `python` が未定義なことがあるため、`python-is-python3` も合わせて入れて `python` コマンドを通す。
- `unixodbc` は ODBC ランタイム、`unixodbc-dev` は開発ヘッダ。

### 3. `msodbcsql18` を入れる

Microsoft の Ubuntu 用パッケージリポジトリを登録してからインストールする。

```bash
curl -sSL -O https://packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb

sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18
```

補足:

- `scripts/init/sql/deploy.sh` と backend 側の DB 接続は `ODBC Driver 18 for SQL Server` を前提とする。

### 4. `azure-cli` を入れる

```bash
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

sudo mkdir -p /etc/apt/keyrings
curl -sLS https://packages.microsoft.com/keys/microsoft.asc | \
  gpg --dearmor | sudo tee /etc/apt/keyrings/microsoft.gpg > /dev/null
sudo chmod go+r /etc/apt/keyrings/microsoft.gpg

AZ_DIST=$(lsb_release -cs)
echo "Types: deb
URIs: https://packages.microsoft.com/repos/azure-cli/
Suites: ${AZ_DIST}
Components: main
Architectures: $(dpkg --print-architecture)
Signed-by: /etc/apt/keyrings/microsoft.gpg" | sudo tee /etc/apt/sources.list.d/azure-cli.sources

sudo apt-get update
sudo apt-get install -y azure-cli
```

補足:

- maint-vm では `az login --identity --client-id <MIGRATION_MI_CLIENT_ID>` で migration 用 Managed Identity を明示して使う運用を基本とする。

### 5. `uv` を入れる

Astral 公式インストーラでユーザー領域へ導入する。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

シェルを再読み込みする。

```bash
source ~/.bashrc
```

`~/.local/bin` が `PATH` に入っていない場合は追加する。

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 6. backend 依存を入れる

リポジトリルートで以下を実行する。

```bash
cd /path/to/3pull/apps/backend
uv sync --frozen
```

補足:

- `pyodbc` はこの `uv sync --frozen` で Python 環境に入る。
- `deploy.sh` は `uv --directory apps/backend run python` を優先して使う。
- `make alembic-upgrade` も `uv run alembic upgrade head` を使う。

### 7. 認証に使う Managed Identity を明示する

VM に複数の User Assigned Managed Identity を付ける前提なので、migration 用 principal を明示する。

```bash
export AZURE_CLIENT_ID="<MIGRATION_MI_CLIENT_ID>"
az login --identity --client-id "$AZURE_CLIENT_ID"
```

補足:

- backend 側の `DefaultAzureCredential()` も `AZURE_CLIENT_ID` が設定されていると対象 identity を選びやすい。
- `make alembic-upgrade` は Azure SQL 用 access token をコード側で取得する。

### 8. backend 用環境変数を用意する

少なくとも `DATABASE_URL` が必要。

```bash
cp /path/to/3pull/apps/backend/.env.example /path/to/3pull/apps/backend/.env
```

`apps/backend/.env` で最低限以下を設定する。

```dotenv
DATABASE_URL=mssql+pyodbc://@<sql-server-fqdn>/<database-name>?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
```

通常モードの `deploy.sh` を使う場合は、`scripts/init/sql/param.conf` も必要。

### 9. AKS 運用ツールを入れる

AKS 運用を行う場合は、少なくとも以下を maint-vm へ導入する。

- `kubectl`
- `helm`
- `kubelogin`

補足:

- `kubelogin` は Azure RBAC/AAD ベースの kubeconfig を `kubectl` から利用するために必要。

## 動作確認

### 基本コマンド確認

```bash
git --version
make --version
python --version
python3.12 --version
uv --version
az version
odbcinst -j
```

### ODBC Driver 18 確認

```bash
odbcinst -q -d | grep "ODBC Driver 18 for SQL Server"
```

### backend 依存確認

```bash
cd /path/to/3pull/apps/backend
uv run python -c "import pyodbc; print(pyodbc.version)"
```

### 実行例

通常モードで bootstrap:

```bash
cd /path/to/3pull
./scripts/init/sql/deploy.sh
```

Alembic 適用:

```bash
cd /path/to/3pull
make alembic-upgrade
```

## 参考

- Azure CLI on Linux: https://learn.microsoft.com/cli/azure/install-azure-cli-linux
- Microsoft ODBC Driver 18 for SQL Server on Linux: https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server
- uv installer: https://docs.astral.sh/uv/reference/installer/
