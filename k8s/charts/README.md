# Helm Charts

`k8s/charts/` 配下には、AKS へデプロイするための Helm chart を置きます。

- `backend/`
  - FastAPI API / worker / schedulers を載せるための chart
  - 現時点では API 用 `Deployment` / `Service`、worker 用 `Deployment`、schedulers 用 `CronJob` まで実装済み
- `frontend/`
  - frontend web を載せるための chart
  - `Deployment` / `Service` の最小構成を実装済み

## Chart の基本構成

各 chart は、概ね以下の構成で持ちます。

```text
<chart-name>/
├── Chart.yaml
├── values.yaml
├── values.staging.yaml
├── values.prod.yaml
└── templates/
    ├── _helpers.tpl
    ├── ...
```

### `Chart.yaml`

chart 自体のメタ情報です。

- chart 名
- バージョン
- chart の種別（`application`）

を定義します。

これは Helm が chart を識別するために使います。

### `values.yaml`

chart のデフォルト設定です。

- image repository / tag
- replica 数
- `ServiceAccount` 名
- `Service` の port
- ConfigMap に入れる環境変数

のような「通常の既定値」をここに置きます。

最初に読み込まれるベース設定と考えてください。

### `values.staging.yaml` / `values.prod.yaml`

環境ごとの差分だけを上書きするファイルです。

例えば:

- staging だけ URL が違う
- prod だけログレベルを変える
- prod だけ replica 数を増やす

といった差分をここに書きます。

`values.yaml` を丸ごと複製する場所ではなく、「差分だけを書くファイル」です。

### `templates/`

Kubernetes manifest のテンプレートです。

ここにあるファイルは、Helm 実行時に `values` を埋め込まれて最終的な YAML に変換されます。

例:

- `Deployment`
- `Service`
- `ConfigMap`
- `ServiceAccount`
- 将来追加する `CronJob` / `ScaledObject`

### `templates/_helpers.tpl`

他の template から共通利用する補助関数です。

このプロジェクトでは主に以下をまとめています。

- 名前生成
- namespace 解決
- label 共通化

例えば `include "backend.fullname" .` のように他の template から呼ばれます。

## backend chart の各ファイル

`backend/` は現時点で以下の役割です。

- `Chart.yaml`
  - backend chart のメタ情報
- `values.yaml`
  - backend の既定値
  - 現時点では API / worker / schedulers 用 values、共通 ConfigMap、Key Vault 連携、Secret 参照、ServiceAccount 設定を持つ
- `values.staging.yaml`
  - staging 用の差分値
- `values.prod.yaml`
  - prod 用の差分値
- `templates/_helpers.tpl`
  - backend chart 共通の name / labels / namespace helper
- `templates/configmap.yaml`
  - `config.env` から `ConfigMap` を生成
- `templates/serviceaccounts.yaml`
  - `serviceAccounts.*.create` が `true` のときに `ServiceAccount` を生成
- `templates/secretproviderclass.yaml`
  - Azure Key Vault の secret を CSI Driver 経由で Kubernetes `Secret` に同期するための `SecretProviderClass`
- `templates/api-deployment.yaml`
  - API 用 `Deployment` を生成
- `templates/api-service.yaml`
  - API 用 `Service` を生成
- `templates/worker-deployments.yaml`
  - worker 用 `Deployment` を生成
- `templates/schedulers-cronjobs.yaml`
  - schedulers 用 `CronJob` を生成
- `templates/keda-triggerauthentication.yaml`
  - KEDA が Azure Service Bus を読むための `TriggerAuthentication` を生成
- `templates/keda-scaledobjects.yaml`
  - worker 用 `ScaledObject` を生成

未実装の主な対象:

- worker / schedulers 用の個別スケール調整値の詳細化

## frontend chart の各ファイル

`frontend/` は現時点で以下の役割です。

- `Chart.yaml`
  - frontend chart のメタ情報
- `values.yaml`
  - frontend の既定値
  - image 設定、replica 数などを持つ
- `values.staging.yaml`
  - staging 用の差分値
- `values.prod.yaml`
  - prod 用の差分値
- `templates/_helpers.tpl`
  - frontend chart 共通の helper
- `templates/deployment.yaml`
  - frontend 用 `Deployment` を生成
- `templates/service.yaml`
  - frontend 用 `Service` を生成

## 実行時の流れ

Helm は「template を上から順に実行する」というより、chart 全体を読み込み、values をマージしてから template をまとめて render します。

処理イメージは次です。

1. `Chart.yaml` を読む
2. `values.yaml` を読む
3. `-f values.staging.yaml` や `-f values.prod.yaml` を指定した場合、その内容で上書きする
4. `templates/` 配下の各 template を読み込む
5. `templates/_helpers.tpl` の helper を解決する
6. `.Values` にマージ済みの値を入れて、各 template を render する
7. 完成した Kubernetes manifest を出力する
8. `helm upgrade --install` の場合は、その manifest を Kubernetes API に apply する

つまり、`values` が先、`templates` は後です。

## `values.yaml` と `values.staging.yaml` / `values.prod.yaml` の違い

例えば次のコマンド:

```bash
helm template 3pull-backend ./k8s/charts/backend \
  -n 3pull \
  -f ./k8s/charts/backend/values.yaml \
  -f ./k8s/charts/backend/values.staging.yaml
```

この場合、Helm は:

1. `values.yaml` の値を読み込む
2. `values.staging.yaml` に同じキーがあれば、その値で上書きする

という動きをします。

例:

```yaml
# values.yaml
api:
  replicaCount: 1
```

```yaml
# values.prod.yaml
api:
  replicaCount: 3
```

このとき prod では最終的に `replicaCount: 3` になります。

指定しなかったキーは `values.yaml` 側の値が残ります。

## よく使うコマンド

### render 結果だけ確認する

```bash
helm template 3pull-backend ./k8s/charts/backend \
  -n 3pull \
  -f ./k8s/charts/backend/values.yaml \
  -f ./k8s/charts/backend/values.staging.yaml
```

これは Kubernetes へは反映せず、最終 manifest を標準出力に出します。

frontend の render は次です。

```bash
helm template 3pull-frontend ./k8s/charts/frontend \
  -n 3pull \
  -f ./k8s/charts/frontend/values.yaml \
  -f ./k8s/charts/frontend/values.staging.yaml
```

### dry-run でインストール確認する

```bash
helm upgrade --install 3pull-backend ./k8s/charts/backend \
  -n 3pull \
  --create-namespace \
  -f ./k8s/charts/backend/values.yaml \
  -f ./k8s/charts/backend/values.staging.yaml \
  --dry-run
```

これは install/update 相当の処理をシミュレーションしますが、実際には反映しません。

frontend の dry-run は次です。

```bash
helm upgrade --install 3pull-frontend ./k8s/charts/frontend \
  -n 3pull \
  --create-namespace \
  -f ./k8s/charts/frontend/values.yaml \
  -f ./k8s/charts/frontend/values.staging.yaml \
  --dry-run
```

### 実際にデプロイする

```bash
helm upgrade --install 3pull-backend ./k8s/charts/backend \
  -n 3pull \
  --create-namespace \
  -f ./k8s/charts/backend/values.yaml \
  -f ./k8s/charts/backend/values.staging.yaml
```

これで render された manifest が Kubernetes に作成・更新されます。

frontend も同様に、chart パスだけ `./k8s/charts/frontend` に変えて実行します。

frontend の実デプロイは次です。

```bash
helm upgrade --install 3pull-frontend ./k8s/charts/frontend \
  -n 3pull \
  --create-namespace \
  -f ./k8s/charts/frontend/values.yaml \
  -f ./k8s/charts/frontend/values.staging.yaml
```

## このプロジェクトでの注意点

- backend chart は API / worker / schedulers / KEDA `ScaledObject` までは実装済み
- `serviceAccounts.*.create=true` を既定とし、`ServiceAccount` も Helm 管理を正とする
  - すでに手動作成済みの同名 `ServiceAccount` がある場合は、Helm 再適用前に削除して切り替える
- `keyVault.enabled=true` の場合は、AKS 側で `azure-keyvault-secrets-provider` add-on が有効であることが前提
  - 例: `az aks enable-addons --addons azure-keyvault-secrets-provider --resource-group 3pull-app --name 3pull-test-cluster`
- `SecretProviderClass` による Kubernetes `Secret` 同期は、Pod が CSI volume を mount して初めて生成される
  - そのため API Pod は `backend-secrets` を `envFrom` 参照しつつ、同時に `secrets-store.csi.k8s.io` volume も mount する
- frontend は現在 `Vite` の静的 build を `nginx` で配信している
  - `VITE_*` は本来 build 時に確定する値
  - そのため frontend chart では `VITE_*` を runtime values としては持たない
  - `VITE_BACKEND_BASE_URL` と `VITE_PRODUCT_NAME` は `docker/web.Dockerfile` の build arg で渡す
