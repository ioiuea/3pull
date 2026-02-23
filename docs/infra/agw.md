# ApplicationGateway

- ※[]内は`infra/common.parameter.json`の設定値に従って設定されます。

## 基本

| 項目         | 設定値                             | Bicepプロパティ名 |
| ------------ | ---------------------------------- | ----------------- |
| 名前         | agw-[common.environmentName]-[common.systemName] | name              |
| 場所         | [common.location]                  | location          |
| マネージドID | -                                  | identity          |

## 診断設定

- 対象: Application Gateway（`Microsoft.Network/applicationGateways`）
- ログ: `allLogs`
- メトリック: `AllMetrics`
- 送信先: Log Analytics

## 削除ロック

- Application Gateway 本体に削除ロックを適用
- WAF Policy に削除ロックを適用
- Public IP に削除ロックを適用

## SKU

| 項目   | 設定値 | Bicepプロパティ名 |
| ------ | ------ | ----------------- |
| 名前   | WAF_v2 | name              |
| サイズ | WAF_v2 | tier              |
| 容量   | 1      | capacity          |

## ゲートウェイIP構成

| 項目         | 設定値                                                       | Bicepプロパティ名    |
| ------------ | ------------------------------------------------------------ | -------------------- |
| 名前         | appGatewayIpConfig                                           | name                 |
| サブネットID | vnet-[common.environmentName]-[common.systemName]/ApplicationGatewaySubnet | properties.subnet.id |

## フロントエンドIP構成

| 項目                       | 設定値                                                       | Bicepプロパティ名                    |
| -------------------------- | ------------------------------------------------------------ | ------------------------------------ |
| 名前                       | appGatewayFrontendPrivateIP                                  | name                                 |
| プライベートIP割り当て方法 | Static                                                       | properties.privateIPAllocationMethod |
| プライベートIPアドレス     | [ApplicationGatewaySubnetのレンジの10個目のIP]               | properties.privateIPAddress          |
| サブネットID               | vnet-[common.environmentName]-[common.systemName]/ApplicationGatewaySubnet | properties.subnet.id                 |

| 項目                       | 設定値                                 | Bicepプロパティ名                    |
| -------------------------- | -------------------------------------- | ------------------------------------ |
| 名前                       | appGatewayFrontendPublicIP             | name                                 |
| プライベートIP割り当て方法 | -                                      | properties.privateIPAllocationMethod |
| プライベートIPアドレス     | -                                      | properties.privateIPAddress          |
| パブリックIPアドレスID     | pip-agw-[common.environmentName]-[common.systemName] | properties.publicIPAddress.id        |

## フロントエンドポート

※これはリソース作成時に必須の項目のため仮のパラメータを記述しているが、後ほど実行するAKSマニフェストで上書きされる。
| 項目 | 設定値 | Bicepプロパティ名 |
|------|------|------|
| 名前 | appGatewayFrontendPort | name |
| ポート | 80 | properties.port |

## バックエンドプール

※これはリソース作成時に必須の項目のため仮のパラメータを記述しているが、後ほど実行するAKSマニフェストで上書きされる。
| 項目 | 設定値 | Bicepプロパティ名 |
|------|------|------|
| 名前 | appGatewayBackendPool | name |
| バックエンドアドレスリスト | - | properties.backendAddresses |

## バックエンドHTTP設定

※これはリソース作成時に必須の項目のため仮のパラメータを記述しているが、後ほど実行するAKSマニフェストで上書きされる。
| 項目 | 設定値 | Bicepプロパティ名 |
|------|------|------|
| 名前 | appGatewayBackendHttpSettings | name |
| ポート | 80 | properties.port |
| プロトコル | Http | properties.protocol |
| Cookieベースのセッションアフィニティ | Enabled | properties.cookieBasedAffinity |
| タイムアウト | 60 | properties.requestTimeout |
| プローブID | appGatewayProbe | properties.probe.id |

## リスナー

※これはリソース作成時に必須の項目のため仮のパラメータを記述しているが、後ほど実行するAKSマニフェストで上書きされる。
| 項目 | 設定値 | Bicepプロパティ名 |
|------|------|------|
| 名前 | appGatewayHttpListener | name |
| フロントエンドIP構成 | appGatewayFrontendPrivateIP | properties.frontendIPConfiguration.id |
| フロントエンドポート | appGatewayFrontendPort | properties.frontendPort.id |
| プロトコル | Http | properties.protocol |

## ルール

※これはリソース作成時に必須の項目のため仮のパラメータを記述しているが、後ほど実行するAKSマニフェストで上書きされる。
| 項目 | 設定値 | Bicepプロパティ名 |
|------|------|------|
| 名前 | appGatewayRule | name |
| 種類 | Basic | properties.ruleType |
| リスナー | appGatewayHttpListener | properties.httpListener.id |
| バックエンドプール | appGatewayBackendPool | properties.backendAddressPool.id |
| バックエンドHTTP設定 | appGatewayBackendHttpSettings | properties.backendHttpSettings.id |
| 優先度 | 1 | properties.priority |

## プローブ

※これはリソース作成時に必須の項目のため仮のパラメータを記述しているが、後ほど実行するAKSマニフェストで上書きされる。
| 項目 | 設定値 | Bicepプロパティ名 |
|------|------|------|
| 名前 | appGatewayProbe | name |
| プロトコル | Http | properties.protocol |
| ホスト | www.contoso.com | properties.host |
| パス | /path/to/probe | properties.path |
| インターバル | 30 | properties.interval |
| タイムアウト | 120 | properties.timeout |
| 閾値 | 8 | properties.unhealthyThreshold |

## WAFポリシー

| 項目 | 設定値                             | Bicepプロパティ名 |
| ---- | ---------------------------------- | ----------------- |
| ID   | waf-[common.environmentName]-[common.systemName] | id                |

# パブリックIPアドレス

| IPアドレス名                           | 概要  |
| -------------------------------------- | ----- |
| pip-agw-[common.environmentName]-[common.systemName] | AGW用 |

##　基本
| 項目 | 設定値 | Bicepプロパティ名 |
|------|------|------|
| 名前 | pip-agw-[common.environmentName]-[common.systemName] | name |
| 場所 | [common.location] | location |
| sku | Standard | sku.name |
| IPアドレス割り当て方法 | Static | properties.publicIPAllocationMethod |
| IPアドレスバージョン | IPv4 | properties.publicIPAddressVersion |
| DDOS保護 | `network.enableDdosProtection=true` の場合は Enabled、`false` の場合は Disabled | properties.ddosSettings.protectionMode |

# WebApplicationFirewall Policy

## 基本

| 項目 | 設定値                             | Bicepプロパティ名 |
| ---- | ---------------------------------- | ----------------- |
| 名前 | waf-[common.environmentName]-[common.systemName] | name              |
| 場所 | [common.location]                  | location          |

## カスタムルール

| 項目 | 設定値 | Bicepプロパティ名 |
| ---- | ------ | ----------------- |
| -    | -      | -                 |

## 管理されているルール

| 項目         | 設定値 | Bicepプロパティ名              |
| ------------ | ------ | ------------------------------ |
| ルールセット | OWASP  | managedRuleSets.ruleSetType    |
| バージョン   | 3.2    | managedRuleSets.ruleSetVersion |

## 除外

| 項目 | 設定値 | Bicepプロパティ名 |
| ---- | ------ | ----------------- |
| -    | -      | -                 |

## ポリシー設定

| 項目                             | 設定値    | Bicepプロパティ名           |
| -------------------------------- | --------- | --------------------------- |
| モード                           | Detection | mode                        |
| 状態                             | Enabled   | state                       |
| 要求本文の検査                   | true      | requestBodyCheck            |
| 要求本文検査の最大サイズ         | 2000      | requestBodyInspectLimitInKB |
| 要求本文の最大サイズ             | 2000      | maxRequestBodySizeInKb      |
| ファイルアップロードの最大サイズ | 100       | fileUploadLimitInMb         |
