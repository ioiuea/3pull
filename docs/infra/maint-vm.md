# ネットワークインターフェース

| NIC名                                       | 概要                  |
| ------------------------------------------- | --------------------- |
| nic-vm-[common.environmentName]-[common.systemName]-maint | メンテナンスVM用のNIC |

## 基本

| 項目 | 設定値                                      | Bicepプロパティ名 |
| ---- | ------------------------------------------- | ----------------- |
| 名前 | nic-vm-[common.environmentName]-[common.systemName]-maint | name              |
| 場所 | [common.location]                                  | location          |

## 診断設定

- 対象: NIC（`Microsoft.Network/networkInterfaces`）
- メトリック: `AllMetrics`
- 送信先: Log Analytics

## 削除ロック

- NIC に削除ロックを適用
- OS Disk に削除ロックを適用
- VM 本体に削除ロックを適用

## IP構成

| 項目                       | 設定値                | Bicepプロパティ名                                                |
| -------------------------- | --------------------- | ---------------------------------------------------------------- |
| 名前                       | ipconfig              | properties.ipConfigurations.name                                 |
| プライベートIP割り当て方法 | Dynamic               | properties.ipConfigurations.properties.privateIPAllocationMethod |
| サブネットのID             | id(MaintenanceSubnet) | properties.ipConfigurations.properties.subnet.id                 |

# 仮想マシン

| VM名                                    | 概要           |
| --------------------------------------- | -------------- |
| vm-[common.environmentName]-[common.systemName]-maint | メンテナンスVM |

## 基本

| 項目 | 設定値                                  | Bicepプロパティ名 |
| ---- | --------------------------------------- | ----------------- |
| 名前 | vm-[common.environmentName]-[common.systemName]-maint | name              |
| 場所 | [common.location]                              | location          |
| ID   | `UserAssigned`                          | identity.type     |

## ハードウェア情報

| 項目   | 設定値           | Bicepプロパティ名                 |
| ------ | ---------------- | --------------------------------- |
| サイズ | Standard_D4as_v5 | properties.hardwareProfile.vmSize |

## OS情報

| 項目           | 設定値                                  | Bicepプロパティ名                  |
| -------------- | --------------------------------------- | ---------------------------------- |
| コンピュータ名 | vm-[common.environmentName]-[common.systemName]-maint | properties.osProfile.computerName  |
| 管理者ユーザ名 | adminUser                               | properties.osProfile.adminUsername |

## ストレージ情報

| 項目                               | 設定値           | Bicepプロパティ名                                               |
| ---------------------------------- | ---------------- | --------------------------------------------------------------- |
| 発行者                             | canonical        | properties.storageProfile.imageReference.publisher              |
| オファー                           | ubuntu-24_04-lts | properties.storageProfile.imageReference.offer                  |
| SKU                                | server           | properties.storageProfile.imageReference.sku                    |
| バージョン                         | latest           | properties.storageProfile.imageReference.version                |
| OSディスク作成オプション           | FromImage        | properties.storageProfile.osDisk.createOption                   |
| OSディスクサイズ                   | 512              | properties.storageProfile.osDisk.diskSizeGB                     |
| マネージドディスクアカウントタイプ | Premium_LRS      | properties.storageProfile.osDisk.managedDisk.storageAccountType |

## ネットワーク情報

| 項目                             | 設定値                                          | Bicepプロパティ名                              |
| -------------------------------- | ----------------------------------------------- | ---------------------------------------------- |
| ネットワークインターフェースのID | id(nic-vm-[common.environmentName]-[common.systemName]-maint) | properties.networkProfile.networkInterfaces.id |

## 診断情報

| 項目             | 設定値 | Bicepプロパティ名                                     |
| ---------------- | ------ | ----------------------------------------------------- |
| ブート診断有効化 | true   | properties.diagnosticsProfile.bootDiagnostics.enabled |

## セキュリティ情報

| 項目                   | 設定値 | Bicepプロパティ名                                         |
| ---------------------- | ------ | --------------------------------------------------------- |
| セキュアブートの有効化 | true   | properties.securityProfile.uefiSettings.secureBootEnabled |
| vTPMの有効化           | true   | properties.securityProfile.uefiSettings.vTpmEnabled       |

# EntraIDログイン有効化手順

## VM本体の構成

- migration 用 User Assigned Managed Identity（`mi-[common.environmentName]-[common.systemName]-migration`）を VM に割り当てる。
- redis 運用用 User Assigned Managed Identity（`mi-[common.environmentName]-[common.systemName]-redis-ops`）を VM に割り当てる。
- AKS 日常運用用 User Assigned Managed Identity（`mi-[common.environmentName]-[common.systemName]-aks-operator`）を VM に割り当てる。
- AKS 高権限運用用 User Assigned Managed Identity（`mi-[common.environmentName]-[common.systemName]-aks-admin`）を VM に割り当てる。
- ACR 運用用 User Assigned Managed Identity（`mi-[common.environmentName]-[common.systemName]-acr-admin`）を VM に割り当てる。
- Key Vault 運用用 User Assigned Managed Identity（`mi-[common.environmentName]-[common.systemName]-kv-admin`）を VM に割り当てる。
- ログインするアカウントに、本VMに対して以下どちらかの権限が付与されていること。
  - 仮想マシン管理者ログイン
  - 仮想マシンユーザーログイン

補足:

- migration 用 User Assigned Managed Identity は Azure SQL bootstrap / Alembic 実行用の principal として利用します。
- redis-ops 用 User Assigned Managed Identity は Azure Managed Redis の block key 確認・解除用 principal として利用します。
- aks-operator 用 User Assigned Managed Identity は AKS の kubeconfig 取得、日常の `kubectl`、アプリ namespace の `helm` 実行用 principal として利用します。
- aks-admin 用 User Assigned Managed Identity は AGIC / KEDA 導入や緊急時の cluster-wide 操作用 principal として利用します。
- acr-admin 用 User Assigned Managed Identity は ACR ログイン、Docker image の build / push 用 principal として利用します。
- kv-admin 用 User Assigned Managed Identity は Key Vault secret 登録・更新用 principal として利用します。
- runtime 用の API / worker / schedulers Managed Identity は maint-vm には割り当てません。
- maint-vm の SystemAssigned は利用しません。

## ネットワーク

以下宛先へのアクセスが許可されている必要がある

- https://packages.microsoft.com: パッケージのインストールとアップグレード用。
- http://169.254.169.254: Azure Instance Metadata Service エンドポイント。
- https://login.microsoftonline.com: PAM ベース (プラグ可能な認証モジュール) の認証フロー用。
- https://pas.windows.net: Azure RBAC フロー用。

## 有効化手順

- 以下コマンドでAADログイン拡張機能を有効化。

```
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group rg-[common.environmentName]-[common.systemName]-maint \
    --vm-name vm-[common.environmentName]-[common.systemName]-maint
```

### ログイン手順

- 以下コマンドを実行し、画面の指示に従いログインを行う。

```
az login
```

- VMへログインする。

```
az ssh vm -n vm-[common.environmentName]-[common.systemName]-maint -g rg-[common.environmentName]-[common.systemName]-maint
```

# migration 実行方針

## 位置づけ

- maint-vm は Azure SQL Database の bootstrap / migration 実行地点とする。
- runtime principal とは別に、migration 専用 Managed Identity を用いる。

## 利用するManaged Identity

| 用途 | Managed Identity | 備考 |
| --- | --- | --- |
| Azure SQL bootstrap / Alembic | `mi-[common.environmentName]-[common.systemName]-migration` | User Assigned Managed Identity |

## 想定する実行内容

- `scripts/init/sql/deploy.sh`
- `make alembic-upgrade`
- 必要に応じた SQL / Alembic の手動実行

セットアップ手順は [maint-vm-setup.md](/Users/hiroki.ueda/Dev/3pull/docs/infra/maint-vm-setup.md) を参照する。

## 設計意図

- API / worker / schedulers に DDL 権限を持たせない
- Private Endpoint 経由で Azure SQL へ到達できる管理経路を maint-vm に集約する
- migration 実行主体を固定し、監査・切り分けをしやすくする
- Redis 解除運用主体を runtime principal と分離し、maint-vm に集約する
- VM の identity は DB 用 1 つ、Redis 用 1 つ、AKS 用 2 つ、ACR 用 1 つ、Key Vault 用 1 つの計 6 principal に分離する

# ACR 運用実行方針

## 位置づけ

- maint-vm は ACR への image push 実行地点とする。
- 個人アカウントではなく、ACR 用 Managed Identity を使って `az acr login` と `docker buildx build --push` を実行する。
- ACR 運用 principal は DB / AKS 運用 principal と分離する。

## 利用する Managed Identity

| 用途 | Managed Identity | 備考 |
| --- | --- | --- |
| ACR 運用 | `mi-[common.environmentName]-[common.systemName]-acr-admin` | User Assigned Managed Identity |

## 想定する実行内容

- `az acr login --name cr[environmentName][systemName]`
- `make docker-build`
- `make docker-push`

## 実行時の前提

- VM に複数 UAMI を割り当てるため、Azure CLI ログイン時は `--client-id` を付けて利用する principal を明示する。
- ACR は Private Endpoint 前提のため、maint-vm から ACR Private Endpoint へ名前解決・疎通できることを前提とする。
- ACR 側には `AcrPush` RBAC を付与する。

例:

```shell
az login --identity --client-id <ACR_ADMIN_MANAGED_IDENTITY_CLIENT_ID>
az acr login --name cr[environmentName][systemName]
```

## 設計意図

- 個人アカウントを使った ACR ログインを避け、条件付きアクセスの影響を受けにくい運用経路を持つ
- image build / push を専用 principal に分離し、AKS や DB の権限と混在させない
- 将来 GitHub Actions や self-hosted runner へ寄せる際の principal 分離方針を先に揃える

# Key Vault 運用実行方針

## 位置づけ

- maint-vm は Key Vault への secret 登録・更新実行地点とする。
- 個人アカウントではなく、Key Vault 用 Managed Identity を使って `az keyvault secret set` を実行する。
- Key Vault 運用 principal は DB / AKS / ACR 運用 principal と分離する。

## 利用する Managed Identity

| 用途 | Managed Identity | 備考 |
| --- | --- | --- |
| Key Vault 運用 | `mi-[common.environmentName]-[common.systemName]-kv-admin` | User Assigned Managed Identity |

## 想定する実行内容

- `az keyvault secret set`
- Key Vault secret の更新・ローテーション

## 実行時の前提

- VM に複数 UAMI を割り当てるため、Azure CLI ログイン時は `--client-id` を付けて利用する principal を明示する。
- Key Vault は Private Endpoint 前提のため、maint-vm から Key Vault Private Endpoint へ名前解決・疎通できることを前提とする。
- Key Vault 側には `Key Vault Secrets Officer` RBAC を付与する。

例:

```shell
az login --identity --client-id <KV_ADMIN_MANAGED_IDENTITY_CLIENT_ID>
az keyvault secret set --vault-name kv-[environmentName]-[systemName] --name sample --value sample
```

## 設計意図

- 個人アカウントを使った Key Vault 操作を避け、条件付きアクセスの影響を受けにくい運用経路を持つ
- secret 登録・更新を専用 principal に分離し、AKS / ACR / DB の権限と混在させない

# AKS 運用実行方針

## 位置づけ

- maint-vm は AKS への運用アクセス起点とする。
- 個人アカウントではなく、AKS 用 Managed Identity を使って `kubectl` / `helm` を実行する。
- DB 運用 principal と AKS 運用 principal は分離する。
- AKS は日常運用用 (`aks-operator`) と高権限運用用 (`aks-admin`) を分離する。

## 利用する Managed Identity

| 用途 | Managed Identity | 備考 |
| --- | --- | --- |
| AKS 日常運用 | `mi-[common.environmentName]-[common.systemName]-aks-operator` | User Assigned Managed Identity |
| AKS 高権限運用 | `mi-[common.environmentName]-[common.systemName]-aks-admin` | User Assigned Managed Identity |

## 想定する実行内容

`aks-operator`:

- `az aks get-credentials`
- `kubectl get|describe|logs`
- app namespace の `kubectl apply`
- app namespace の `helm upgrade --install`

`aks-admin`:

- AGIC / KEDA の初期導入・更新
- CRD / ClusterRole / ClusterRoleBinding を含む変更
- namespace 作成や cluster-wide 設定変更
- 緊急時の高権限 `kubectl` 操作

## 実行時の前提

- VM に複数 UAMI を割り当てるため、Azure CLI ログイン時は `--client-id` を付けて利用する principal を明示する。
- AKS は Private Cluster のため、maint-vm から AKS Private FQDN へ名前解決・疎通できることを前提とする。
- AAD/Azure RBAC ベースの kubeconfig を利用する。

例:

```shell
az login --identity --client-id <AKS_OPERATOR_MANAGED_IDENTITY_CLIENT_ID>
az aks get-credentials \
  --resource-group rg-[common.environmentName]-[common.systemName]-svc \
  --name aks-[common.environmentName]-[common.systemName] \
  --overwrite-existing
```

## 設計意図

- `migration` MI に AKS 権限を持たせず、DB と Kubernetes の権限境界を分ける
- 日常の調査・アプリ配備は `aks-operator`、初期構築・緊急作業は `aks-admin` に分離する
- AGIC / KEDA のような cluster-wide 操作を `aks-admin` に閉じ込める
- 緊急時の `kubectl` 操作も、個人権限ではなく監査しやすい高権限 principal に寄せる
- runtime 用 Managed Identity を運用端末に露出させない

関連:

- Azure SQL Database: [azure-sql-database.md](./azure-sql-database.md)
- Managed Identity: [managed-id.md](./managed-id.md)
- AKS: [aks.md](./aks.md)
