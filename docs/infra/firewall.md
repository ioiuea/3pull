# Azure FireWall

- ※[]内は`infra/common.parameter.json`の設定値に従って設定されます。

## 基本

| 項目       | 設定値                              | Bicepプロパティ名         |
| ---------- | ----------------------------------- | ------------------------- |
| 名前       | afw-[common.environmentName]-[common.systemName]  | name                      |
| 場所       | [common.location]                   | location                  |
| FWポリシー | afwp-[common.environmentName]-[common.systemName] | properties.FirewallPolicy |

## 診断設定

- 対象1: Azure Firewall（`Microsoft.Network/azureFirewalls`）
  - ログ: `allLogs`
  - メトリック: `allMetrics`
- 対象2: Firewall 用 Public IP（`Microsoft.Network/publicIPAddresses`）
  - メトリック: `AllMetrics`
- 送信先: Log Analytics

## 削除ロック

- Azure Firewall 本体に削除ロックを適用
- Firewall Policy に削除ロックを適用（Policy 新規作成時のみ）
- Firewall 用 Public IP に削除ロックを適用

## IP構成

| 項目                   | 設定値                                     | Bicepプロパティ名                                         |
| ---------------------- | ------------------------------------------ | --------------------------------------------------------- |
| 名前                   | ipconf-afw-[common.environmentName]-[common.systemName]  | properties.IpConfigurations.name                          |
| パブリックIPアドレスID | id(pip-afw-[common.environmentName]-[common.systemName]) | properties.IpConfigurations.properties.publicIPAddress.id |
| サブネットID           | id(AzureFirewallSubnet)                    | properties.IpConfigurations.properties.subnet.id          |

# Azure FireWall Policy

## 基本

| 項目                 | 設定値                              | Bicepプロパティ名          |
| -------------------- | ----------------------------------- | -------------------------- |
| 名前                 | afwp-[common.environmentName]-[common.systemName] | name                       |
| 場所                 | [common.location]                   | location                   |
| 脅威インテリジェンス | Deny                                | properties.threatIntelMode |

## SKU

| 項目   | 設定値                                                                | Bicepプロパティ名   |
| ------ | --------------------------------------------------------------------- | ------------------- |
| サイズ | `network.enableFirewallIdps=true` の場合は Premium、`false` の場合は Standard | properties.sku.tier |

## 侵入検知

| 項目   | 設定値 | Bicepプロパティ名                  |
| ------ | ------ | ---------------------------------- |
| モード | Alert  | properties.intrusionDetection.mode |

# パブリックIPアドレス

| IPアドレス名                           | 概要                 |
| -------------------------------------- | -------------------- |
| pip-afw-[common.environmentName]-[common.systemName] | ファイヤーウォール用 |

##　基本
| 項目 | 設定値 | Bicepプロパティ名 |
|------|------|------|
| 名前 | pip-afw-[common.environmentName]-[common.systemName] | name |
| 場所 | [common.location] | location |
| sku | Standard | sku.name |
| IPアドレス割り当て方法 | Static | properties.publicIPAllocationMethod |
| IPアドレスバージョン | IPv4 | properties.publicIPAddressVersion |
| DDOS保護 | `network.enableDdosProtection=true` の場合は Enabled、`false` の場合は Disabled | properties.ddosSettings.protectionMode |
