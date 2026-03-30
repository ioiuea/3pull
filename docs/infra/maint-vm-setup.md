# Maint VM Setup

Ubuntu で、以下を実行できる状態にするためのセットアップ手順をまとめる。

- `scripts/init/sql/deploy.sh`
- `make alembic-upgrade`
- AKS の日常運用で使う `kubectl` / `helm`

前提:

- VM イメージは Ubuntu 24.04 LTS だとする
- このリポジトリを VM 上に clone 済み
- Azure SQL へのネットワーク疎通は確保済み
- migration 用 User Assigned Managed Identity は VM に割り当て済み

## インストール対象

### APT で入れるもの

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
- `helm`

### ユーザー領域または追加コマンドで入れるもの

- `uv`
- `kubectl`
- `kubelogin`

### 後段で導入・利用するもの

- backend の Python 依存
  - `apps/backend` で `uv sync --frozen` を実行して導入する
- Azure 認証
  - `az login --identity --client-id ...`

## 役割

- `git`: このリポジトリを VM 上に clone / pull するために必要
- `make`: `make alembic-upgrade` の実行に必要
- `apt-transport-https`: APT で HTTPS リポジトリを扱うために必要
- `python-is-python3`: `python` コマンドを `python3` に向けるために必要
- `python3.12`: backend / Alembic / `deploy.sh` の Python 実行基盤として必要
- `python3.12-venv`: Python 仮想環境を扱うために必要になる場合があるため導入
- `curl`: 外部リポジトリ鍵取得、`uv` インストーラ取得に必要
- `ca-certificates`: HTTPS 経由の installer や package repo に安全に接続するために必要
- `gnupg`: APT の外部リポジトリ鍵や署名検証に必要
- `lsb-release`: Ubuntu の distribution codename を取得し、APT repo 設定に使う
- `uv`: backend の Python 依存導入と Alembic 実行に必要
- `unixodbc`: Linux の ODBC マネージャとして必要。`pyodbc` と ODBC ドライバの仲介を行う
- `unixodbc-dev`: `pyodbc` のビルドやヘッダ解決で必要になる場合があるため導入
- `msodbcsql18`: Azure SQL / SQL Server 向け ODBC ドライバ本体として必要
- `azure-cli`: Managed Identity ログイン確認、Azure 運用コマンド、`kubelogin` 導入に必要
- `kubectl`: AKS に対する Kubernetes API 操作用に必要
- `helm`: AKS 上のアプリ / chart デプロイ用に必要
- `kubelogin`: Azure RBAC / Microsoft Entra ベースの kubeconfig を `kubectl` から使うために必要
- `pyodbc`: Python から ODBC 経由で Azure SQL に接続するために必要

## 手順

### 1. APT 用の前提パッケージを入れる

APT 外部リポジトリを追加する前に、鍵管理と HTTPS 通信に必要なパッケージだけ先に入れる。

```bash
sudo apt-get update
sudo apt-get install -y \
  apt-transport-https \
  ca-certificates \
  curl \
  gnupg \
  lsb-release
```

### 2. 外部 APT リポジトリを登録する

#### Microsoft package repo (`msodbcsql18` 用)

```bash
curl -sSL -O https://packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb
```

#### Azure CLI repo

```bash
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
```

#### Helm repo

```bash
curl -fsSL https://packages.buildkite.com/helm-linux/helm-debian/gpgkey | \
  gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/helm.gpg] https://packages.buildkite.com/helm-linux/helm-debian/any/ any main" | \
  sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
```

### 3. 依存パッケージをまとめてインストールする

リポジトリ登録が終わったら、以後の作業に必要な APT パッケージをまとめて入れる。

```bash
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y \
  git \
  make \
  python-is-python3 \
  python3.12 \
  python3.12-venv \
  unixodbc \
  unixodbc-dev \
  msodbcsql18 \
  azure-cli \
  helm
```

補足:

- Ubuntu 24.04 では `python3.12` は標準系だが、明示的に入れておく。
- Ubuntu では `python3` はあっても `python` が未定義なことがあるため、`python-is-python3` も合わせて入れて `python` コマンドを通す。
- `scripts/init/sql/deploy.sh` と backend 側の DB 接続は `ODBC Driver 18 for SQL Server` を前提とする。

### 4. `uv` を入れる

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

### 5. `kubectl` と `kubelogin` を入れる

`azure-cli` の `az aks install-cli` を使って `kubectl` と `kubelogin` をまとめてインストールする。`kubectl` は接続先 cluster と 1 minor 差以内の version を使うため、必要なら `--client-version` で対象 AKS に合わせて固定する。

```bash
sudo az aks install-cli \
  --client-version latest \
  --install-location /usr/local/bin/kubectl \
  --kubelogin-version latest \
  --kubelogin-install-location /usr/local/bin/kubelogin
```

補足:

- `kubelogin` は Azure RBAC / Microsoft Entra ベースの AKS kubeconfig を扱うために必要。
- `kubectl` の version を cluster に合わせて固定したい場合は `--client-version v1.xx.y` を指定する。

## インストール確認

インストール直後に、まず各コマンドが入っていることを確認する。

### 基本コマンド確認

```bash
git --version
make --version
python --version
python3.12 --version
uv --version
az version
kubectl version --client
helm version
kubelogin --version
odbcinst -j
```

### ODBC Driver 18 確認

```bash
odbcinst -q -d | grep "ODBC Driver 18 for SQL Server"
```

### コマンド配置確認

```bash
which python
which uv
which az
which kubectl
which helm
which kubelogin
```

## 後段の作業

パッケージ導入後に、実運用や DB 作業に必要な設定・依存導入を進める。

### 1. backend 依存を入れる

リポジトリルートで以下を実行する。

```bash
cd /path/to/3pull/apps/backend
uv sync --frozen
```

補足:

- `pyodbc` はこの `uv sync --frozen` で Python 環境に入る。
- `deploy.sh` は `uv --directory apps/backend run python` を優先して使う。
- `make alembic-upgrade` も `uv run alembic upgrade head` を使う。

### 2. backend 依存を確認する

```bash
cd /path/to/3pull/apps/backend
uv run python -c "import pyodbc; print(pyodbc.version)"
```

### 3. 認証に使う Managed Identity を明示する

VM に複数の User Assigned Managed Identity を付ける前提なので、migration 用 principal を明示する。

```bash
export AZURE_CLIENT_ID="<MIGRATION_MI_CLIENT_ID>"
az login --identity --client-id "$AZURE_CLIENT_ID"
```

補足:

- maint-vm では `az login --identity --client-id <MIGRATION_MI_CLIENT_ID>` で migration 用 Managed Identity を明示して使う運用を基本とする。
- backend 側の `DefaultAzureCredential()` も `AZURE_CLIENT_ID` が設定されていると対象 identity を選びやすい。
- `make alembic-upgrade` は Azure SQL 用 access token をコード側で取得する。

### 4. backend 用環境変数を用意する

少なくとも `DATABASE_URL` が必要。

```bash
cp /path/to/3pull/apps/backend/.env.example /path/to/3pull/apps/backend/.env
```

`apps/backend/.env` で最低限以下を設定する。

```dotenv
DATABASE_URL=mssql+pyodbc://@<sql-server-fqdn>/<database-name>?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
```

通常モードの `deploy.sh` を使う場合は、`scripts/init/sql/param.conf` も必要。

### 5. 実行例

通常モードで bootstrap:

```bash
cd /path/to/3pull
./scripts/init/sql/deploy.sh
```
