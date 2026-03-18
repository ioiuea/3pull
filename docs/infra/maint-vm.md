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
- ログインするアカウントに、本VMに対して以下どちらかの権限が付与されていること。
  - 仮想マシン管理者ログイン
  - 仮想マシンユーザーログイン

補足:

- migration 用 User Assigned Managed Identity は Azure SQL bootstrap / Alembic 実行用の principal として利用します。
- runtime 用の API / worker / schedulers Managed Identity は maint-vm には割り当てません。

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

## 設計意図

- API / worker / schedulers に DDL 権限を持たせない
- Private Endpoint 経由で Azure SQL へ到達できる管理経路を maint-vm に集約する
- migration 実行主体を固定し、監査・切り分けをしやすくする
- VM の identity は migration 用 principal に絞り、責務を明確にする

関連:

- Azure SQL Database: [azure-sql-database.md](./azure-sql-database.md)
- Managed Identity: [managed-id.md](./managed-id.md)

# パッケージインストール手順

## azure-cliインストール

以下コマンドを実行する

```shell
sudo apt-get update
sudo apt-get install apt-transport-https ca-certificates curl gnupg lsb-release

sudo mkdir -p /etc/apt/keyrings
curl -sLS https://packages.microsoft.com/keys/microsoft.asc |
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
sudo apt-get install azure-cli
```
