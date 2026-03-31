# 3pull

<p>
  <img src="docs/assets/3pull-logo.png" alt="3pull character icon" />
</p>

モノレポ構成の Web + API + Worker + Infra スターターパックです。

## スターター構成

### インフラ

- Infrastructure as Code（Bicep）によるインフラ構築
- インフラ設計/構成ドキュメント（`docs/infra/`）

### フロントエンド（`apps/frontend`）

- Web フレームワーク: React Router v7（Framework Mode / `ssr: false`）
- 認証: FastAPI セッション認証（Entra ID / Email）
- 国際化対応: i18next + react-i18next
- グローバルステート管理: Zustand
- バリデーション: Zod + react-hook-form
- UI フレームワーク: shadcn/ui + Tailwind CSS

### バックエンド（`apps/backend`）

- API フレームワーク: FastAPI
- 構造化ログ: structlog（JSON 出力）
- 設定管理 / バリデーション: Pydantic（pydantic-settings）
- ASGI プロセスマネージャ: Gunicorn

## セットアップ手順

Azure 環境へインフラを構築し、メンテナンス VM から AKS / SQL の初期化を行う一連の流れです。  
詳細なパラメータ説明や構成差分は [infra/README.md](/Users/hiroki.ueda/Dev/3pull/infra/README.md) と [docs/](/Users/hiroki.ueda/Dev/3pull/docs) を参照してください。

### セットアップ準備

1. リポジトリをクローンする
   踏み台サーバなど、Azure 環境へ到達できる作業端末でリポジトリを取得します。

   ```bash
   cd /path/to/workdir
   git clone https://github.com/ioiuea/3pull.git
   ```

2. インフラ構築パラメータを設定する
   [`infra/common.parameter.json`](/Users/hiroki.ueda/Dev/3pull/infra/common.parameter.json) を環境に合わせて更新します。  
   どの項目を変更するかは [infra/README.md](/Users/hiroki.ueda/Dev/3pull/infra/README.md) を見ながら決めてください。

   ```bash
   vi 3pull/infra/common.parameter.json
   ```

### IaCによるAzure作成

3. IaC を 1 回目実行する
   まずは基盤リソース群を作成します。パスワードはサンプル値のまま使わず、必ず置き換えてください。

   ```bash
   cd 3pull/infra
   SQL_ADMIN_LOGIN='sqladmin' \
   SQL_ADMIN_PASSWORD='ReplaceWithStrongPassword1!' \
   MAINT_VM_ADMIN_LOGIN='maintadmin' \
   MAINT_VM_ADMIN_PASSWORD='ReplaceWithStrongPassword2!' \
   ./main.sh
   ```

4. ハブ VNET とのピアリングを行う
   ハブ&スポーク構成の場合は、この時点で VNET ピアリングを設定します。  
   後続の AKS デプロイでは外部通信が必要になるため、先に経路を通しておきます。  
   基本構成でハブ&スポークでなければこの手順は不要です。

### IaCによるその他リソース作成

5. IaC を 2 回目実行する
   ピアリング後に、同じパラメータと同じログイン情報でもう一度 [`infra/main.sh`](/Users/hiroki.ueda/Dev/3pull/infra/main.sh) を実行します。  
   1 回目と同じパスワードを使って問題ありません。

   ```bash
   cd 3pull/infra
   SQL_ADMIN_LOGIN='sqladmin' \
   SQL_ADMIN_PASSWORD='ReplaceWithStrongPassword1!' \
   MAINT_VM_ADMIN_LOGIN='maintadmin' \
   MAINT_VM_ADMIN_PASSWORD='ReplaceWithStrongPassword2!' \
   ./main.sh
   ```

6. 踏み台サーバからメンテナンス VM へ到達できる状態にする
   基本構成では、踏み台サーバを `AzureBastionSubnet` に作成してメンテナンス VM へ接続します。  
   `sharedBastionIp` を使って既存の踏み台を利用する場合は、その踏み台 VM が存在する VNET と今回の VNET の疎通を確保してください。（VNETピアリング実施）

### メンテナンスVMの初期セットアップ

7. 生成済みファイルをメンテナンス VM へコピーする
   踏み台サーバから、リポジトリ全体をメンテナンス VM へ送ります。  
   パスと IP は環境に合わせて置き換えてください。IP はメンテナンス VM のものです。

   ```bash
   scp -r /path/to/3pull maintadmin@10.000.000.000:/home/maintadmin
   ```

8. メンテナンス VM へログインする
   メンテナンス VM の IP、ログイン ID、パスワードは IaC 実行時に指定した値に合わせます。

   ```bash
   ssh maintadmin@10.000.000.000
   ```

9. メンテナンス VM をセットアップする
   初期状態の Ubuntu VM に、`git` / `az` / `kubectl` / `helm` / `kubelogin` / `uv` などの依存関係を導入します。  
   詳細は [docs/infra/maint-vm-setup.md](/Users/hiroki.ueda/Dev/3pull/docs/infra/maint-vm-setup.md) を参照してください。

   ```bash
   /home/maintadmin/3pull/scripts/init/maintvm/setup.sh
   ```

### AKSの初期セットアップ

10. AKS 管理用マネージド ID でログインする
   `mi-<environmentName>-<systemName>-aks-admin` の client ID を Azure Portal で確認して置き換えます。

   ```bash
   az login --identity --client-id "00000000-0000-0000-0000-000000000000"
   ```

11. AGIC コントローラをインストールする
   AKS addon は使わず、生成された Helm スクリプトで AGIC を導入します。

   ```bash
   /home/maintadmin/3pull/scripts/init/agicController/deploy.sh
   ```

   よく使う確認 / 調査コマンド:

   ```bash
   helm list -n ingress
   kubectl logs -n ingress deploy/agic-standard-ingress-azure
   kubectl logs -n ingress deploy/agic-lowlatency-ingress-azure
   kubectl get pods -n ingress -o wide
   kubectl get deployment -n ingress
   ```

   アンインストールコマンド:

   ```bash
   helm uninstall agic-standard -n ingress --no-hooks
   helm uninstall agic-lowlatency -n ingress --no-hooks
   ```

12. KEDA コントローラをインストールする
   KEDA も AKS addon は使わず、生成された Helm スクリプトで導入します。

   ```bash
   /home/maintadmin/3pull/scripts/init/kedaController/deploy.sh
   ```

   よく使う確認 / 調査コマンド:

   ```bash
   helm list -n keda
   kubectl get pods -n keda -o wide
   kubectl get deployment -n keda
   kubectl get secret -n keda kedaorg-certs
   kubectl logs -n keda deploy/keda-operator --tail=100
   ```

### SQL Databaseの初期セットアップ

13. SQL 用マネージド ID でログインする
   `mi-<environmentName>-<systemName>-migration` の client ID を Azure Portal で確認して置き換えます。  
   このログインでは `--allow-no-subscriptions` が必要です。

   ```bash
   az login --identity --client-id "00000000-0000-0000-0000-000000000000" --allow-no-subscriptions
   ```

14. SQL Server の Entra 管理者を一時的に migration MI に変更する
   SQL Server へ Entra 認証で接続し、初期 schema と principal を作成するために必要です。  
   対象は `mi-<environmentName>-<systemName>-migration` です。

15. SQL スキーマと principal を作成する
   生成済みの [`scripts/init/sql/deploy.sh`](/Users/hiroki.ueda/Dev/3pull/scripts/init/sql/deploy.sh) を実行します。  
   実行後は schema / principal / role 付与状況の確認結果も標準出力に表示されます。

   ```bash
   /home/maintadmin/3pull/scripts/init/sql/deploy.sh
   ```

### Databaseの初期マイグレーション

16. backend の依存関係をインストールする
   Alembic migration 実行前に Python 依存関係を揃えます。`pyodbc` が import できることまで確認します。

   ```bash
   cd /home/maintadmin/3pull/apps/backend
   uv sync --frozen
   uv run python -c "import pyodbc; print(pyodbc.version)"
   ```

17. 環境変数を設定する
   `.env.example` を複製して `.env` を作成し、Azure SQL Database の接続先に合わせて更新します。

   ```bash
   cp .env.example .env
   vi .env
   ```

   ```dotenv
   DATABASE_URL=mssql+pyodbc://@your-sql-server.database.windows.net/your-database-name?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
   ```

18. マイグレーションを実行する
   バックエンドの初期テーブルを作成します。

   ```bash
   cd /home/maintadmin/3pull
   make alembic-upgrade
   ```

19. SQL Server の Entra 管理者設定を元に戻す
   初期構築で一時的に migration MI へ切り替えていた場合は、[`infra/common.parameter.json`](/Users/hiroki.ueda/Dev/3pull/infra/common.parameter.json) で管理している本来の Entra 管理者へ戻します。

### Dockerイメージの準備

20. コンテナイメージ用のタグを決める
   Docker image の build / push と Helm deploy で同じ tag を使います。  
   運用方針としては Git commit SHA を tag に使う前提にします。

   ```bash
   cd /home/maintadmin/3pull
   export IMAGE_TAG="$(git rev-parse --short HEAD)"
   echo "$IMAGE_TAG"
   ```

21. ACR 用マネージド ID でログインする
   `mi-<environmentName>-<systemName>-acr-admin` の client ID を Azure Portal で確認して置き換えます。  
   Docker image の build / push と `az acr login` は、この principal で実行します。

   ```bash
   az login --identity --client-id "00000000-0000-0000-0000-000000000000"
   ```

22. ACR へログインする
   メンテナンス VM 上で build / push を行う前提です。  
   ACR 名は `cr<environmentName><systemName>` 形式なので、環境に合わせて置き換えてください。

   ```bash
   az acr login --name cr<environmentName><systemName>
   ```

23. Docker image を build する
   `docker buildx` 前提で image を build します。  
   frontend は build 時に API の公開 URL と製品名を埋め込むため、`VITE_BACKEND_BASE_URL` と `VITE_PRODUCT_NAME` を指定します。

   ```bash
   cd /home/maintadmin/3pull
   export DOCKER_API_IMAGE="cr<environmentName><systemName>.azurecr.io/<systemName>-api:${IMAGE_TAG}"
   export DOCKER_WORKER_IMAGE="cr<environmentName><systemName>.azurecr.io/<systemName>-worker:${IMAGE_TAG}"
   export DOCKER_SCHEDULERS_IMAGE="cr<environmentName><systemName>.azurecr.io/<systemName>-schedulers:${IMAGE_TAG}"
   export DOCKER_WEB_IMAGE="cr<environmentName><systemName>.azurecr.io/<systemName>-web:${IMAGE_TAG}"
   export VITE_BACKEND_BASE_URL="https://api.example.com"
   export VITE_PRODUCT_NAME="<systemName>"
   make docker-build
   ```

24. Docker image を ACR へ push する
   build 済み image を push する代わりに、`docker buildx build --push` をまとめて呼ぶ Make target を使います。

   ```bash
   make docker-push
   ```

### KeyVaultへのシークレット登録

25. Key Vault へシークレット値を登録する
   backend chart は Key Vault を前提に起動するため、Helm deploy 前に登録します。  
   Key Vault 名は `kv-<environmentName>-<systemName>` を置き換えてください。

   ```bash
   export KEY_VAULT_NAME="kv-<environmentName>-<systemName>"

   az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name database-url --value 'mssql+pyodbc://@your-sql-server.database.windows.net/your-database-name?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no'
   az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name applicationinsights-connection-string --value '<ApplicationInsightsConnectionString>'
   az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name session-secret-key --value '<SessionSecretKey>'
   az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name entra-client-secret --value '<EntraClientSecret>'
   az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name entra-token-encryption-key --value '<EntraTokenEncryptionKey>'
   ```

### アプリのデプロイ

26. 生成済み Helm values を確認する
   `infra/main.sh` の post 処理で生成された `k8s/charts/*/values.yaml` を確認し、Ingress の host 名、ACR repository、Key Vault 名などが想定どおりになっているかを見ます。

   ```bash
   vi /home/maintadmin/3pull/k8s/charts/backend/values.yaml
   vi /home/maintadmin/3pull/k8s/charts/frontend/values.yaml
   ```

27. backend chart を render / dry-run で確認する
   先に backend を確認します。  
   初回 deploy の切り分けをしやすくするため、backend を先に deploy する方針です。

   ```bash
   cd /home/maintadmin/3pull
   helm template 3pull-backend ./k8s/charts/backend \
     -n 3pull \
     -f ./k8s/charts/backend/values.yaml

   helm upgrade --install 3pull-backend ./k8s/charts/backend \
     -n 3pull \
     --create-namespace \
     -f ./k8s/charts/backend/values.yaml \
     --set api.image.tag="$IMAGE_TAG" \
     --set workers.authAuditExport.image.tag="$IMAGE_TAG" \
     --set workers.sampleWaitBlob.image.tag="$IMAGE_TAG" \
     --set schedulers.image.tag="$IMAGE_TAG" \
     --dry-run
   ```

28. backend chart を deploy する
   backend 側の Deployment / KEDA / Ingress を適用します。

   ```bash
   helm upgrade --install 3pull-backend ./k8s/charts/backend \
     -n 3pull \
     --create-namespace \
     -f ./k8s/charts/backend/values.yaml \
     --set api.image.tag="$IMAGE_TAG" \
     --set workers.authAuditExport.image.tag="$IMAGE_TAG" \
     --set workers.sampleWaitBlob.image.tag="$IMAGE_TAG" \
     --set schedulers.image.tag="$IMAGE_TAG"
   ```

   確認コマンド:

   ```bash
   helm list -n 3pull
   kubectl get pods -n 3pull -o wide
   kubectl get ingress -n 3pull
   kubectl logs -n 3pull deploy/r-<systemName>-api --tail=100
   ```

29. frontend chart を render / dry-run で確認する
   backend の次に frontend を確認します。

   ```bash
   helm template 3pull-frontend ./k8s/charts/frontend \
     -n 3pull \
     -f ./k8s/charts/frontend/values.yaml

   helm upgrade --install 3pull-frontend ./k8s/charts/frontend \
     -n 3pull \
     --create-namespace \
     -f ./k8s/charts/frontend/values.yaml \
     --set frontend.image.tag="$IMAGE_TAG" \
     --dry-run
   ```

30. frontend chart を deploy する
   frontend の Deployment / Ingress を適用します。

   ```bash
   helm upgrade --install 3pull-frontend ./k8s/charts/frontend \
     -n 3pull \
     --create-namespace \
     -f ./k8s/charts/frontend/values.yaml \
     --set frontend.image.tag="$IMAGE_TAG"
   ```

   確認コマンド:

   ```bash
   helm list -n 3pull
   kubectl get pods -n 3pull -o wide
   kubectl get ingress -n 3pull
   kubectl logs -n 3pull deploy/r-<systemName>-web --tail=100
   ```

### 公開ドメインの設定

31. 公開ドメイン用の証明書を App Gateway へ登録する
   公開 TLS 終端は Application Gateway に寄せる方針です。  
   初回手順では、証明書の登録は手動で行います。  
   対象の証明書は、frontend / backend で使用する公開ドメインに対応したものを用意してください。

32. Ingress の host 名と証明書設定を最終確認する
   `k8s/charts/backend/values.yaml` と `k8s/charts/frontend/values.yaml` の host 名が、実際に公開するドメインと一致していることを確認します。  
   現状の chart では証明書名の annotation は未定義のため、App Gateway 側の listener / rule 構成と合わせて運用してください。

33. 公開 DNS を切り替える
   App Gateway の Public IP を向くように、公開 DNS レコードを設定します。  
   frontend / backend の host 名に対して、それぞれ想定する Public IP へ名前解決されるようにします。

34. 疎通確認を行う
   公開 URL と Pod 状態を確認し、アプリが正常に応答するかを見ます。

   ```bash
   kubectl get pods -n 3pull
   kubectl get ingress -n 3pull
   curl -I https://app.example.com
   curl -I https://api.example.com/backend/health
   ```

35. 今後の CI/CD 方針
   現時点の正式フローは、メンテナンス VM で build / push / deploy を実行する暫定運用です。  
   将来的には、Docker image の build / push を GitHub Actions、AKS への deploy をメンテナンス VM または self-hosted runner 側へ寄せる構成を想定します。

## セットアップ手順（ローカル環境）

### 前提要件

- Node.js / pnpm
- Python 3.12+ / uv
- Azure CLI（`az login` 済み）
- ODBC Driver 18 for SQL Server
- OpenSSL（JWT 鍵生成で使用）
- `kubectl`（AKS / Kubernetes 操作で使用）
- `helm`（Helm chart の render / deploy で使用）

1. インフラを構築する
   `infra/README.md` を参照し、`infra/common.parameter.json` を環境に合わせて編集してから `infra/main.sh` を実行します。  
   これで Azure 環境のインフラを構築します。

2. アプリ依存関係をインストールする（Makefile 運用）
   プロジェクトルートで `make install` を実行します。  
   フロントエンド/バックエンドの依存関係をまとめてセットアップします。

3. Azure SQL Database の初期設定とマイグレーションを適用する
   まず `./scripts/init/sql/deploy.sh --local` を実行して `auth` / `audit` / `core` schema と現在の Entra ユーザー権限を作成し、その後 `make alembic-upgrade` を実行します。

4. 非同期ジョブ用の Blob コンテナを作成する
   `scripts/README.md` を参照して、非同期ジョブ成果物の保存先となる Blob コンテナを作成します。

5. Entra ID の OIDC アプリを作成する
   Entra ID 側で OIDC 用アプリを作成し、クライアントID/シークレット/リダイレクトURIを準備します。

6. 環境変数ファイルを展開して更新する
   まず `make env` で `.env` を生成し、生成後に各 `.env` を環境値に更新します。

7. アプリを起動する
   用途に応じて以下を実行します。
   - 本番相当起動: `make up`
   - 個別起動: `make up-api` / `make up-web`
   - 開発起動: `make dev-api` / `make dev-web`

## 参照先

- Frontend 詳細: `apps/frontend/README.md`
- Backend 詳細: `apps/backend/README.md`
- Infrastructure 詳細: `docs/`
