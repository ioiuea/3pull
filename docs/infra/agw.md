# Application Gateway

- ※ `[]` 内は `infra/common.parameter.json` の設定値に従います。

## 構成

本環境は通常系 App Gateway を標準構成とし、低遅延オプションを有効化した場合に 2 台目を追加します。

- `network.enableLowLatencyApplicationGatewaySubnet=false`
  - 通常系のみ
- `network.enableLowLatencyApplicationGatewaySubnet=true`
  - 通常系 + 低遅延系を追加

## リソース命名

| 用途 | 命名規則 |
| --- | --- |
| 通常系 AppGW | `agw-[common.environmentName]-[common.systemName]` |
| 通常系 Public IP | `pip-agw-[common.environmentName]-[common.systemName]` |
| 通常系 WAF policy | `waf-[common.environmentName]-[common.systemName]` |
| 低遅延系 AppGW | `agw-ll-[common.environmentName]-[common.systemName]` |
| 低遅延系 Public IP | `pip-agw-ll-[common.environmentName]-[common.systemName]` |
| 低遅延系 WAF policy | `waf-ll-[common.environmentName]-[common.systemName]` |

## サブネット配置

| 用途 | サブネット |
| --- | --- |
| 通常系 AppGW | `ApplicationGatewaySubnet` |
| 低遅延系 AppGW | `ApplicationGatewayLowLatencySubnet`（オプション有効時のみ） |

## SKU / WAF

| 項目 | 設定値 |
| --- | --- |
| SKU | `WAF_v2` |
| Capacity | `1` |
| WAF Mode | `Detection` |
| RuleSet | `OWASP 3.2` |

## AGIC 連携（Helm 統一）

AKS addon AGIC は使わず、`infra/main.sh` で Helm リリースを導入します。

| AGIC リリース | ingressClass | 制御対象 AppGW | SA |
| --- | --- | --- | --- |
| `agic-standard` | `azure-application-gateway` | 通常系 AppGW | `agic-standard-sa-ingress-azure` |
| `agic-lowlatency` | `azure-application-gateway-low-latency` | 低遅延系 AppGW | `agic-lowlatency-sa-ingress-azure` |

## RBAC（App Gateway / Subnet 更新権限）

`main.application-gateway-rbac.bicep` で AGIC 用 Managed Identity に App Gateway 更新権限と、Application Gateway 用サブネットの join 権限を付与します。
Managed Identity 自体は `main.managed-ids.bicep` で先に作成されます。

| Managed Identity | 付与対象 |
| --- | --- |
| `mi-[env]-[system]-agic-standard` | 通常系 App Gateway, `ApplicationGatewaySubnet` |
| `mi-[env]-[system]-agic-lowlatency` | 低遅延系 App Gateway, `ApplicationGatewayLowLatencySubnet`（オプション有効時） |

付与ロール:

- App Gateway スコープ: `Contributor`
- Subnet スコープ: `Network Contributor`

## 低遅延系の意図

低遅延系 AppGW は、用途限定 API を通常系と分離するための入口です。

- 通常系とドメインを分離（例: `api-*` / `ll-api-*`）
- IngressClass を分離して同一 AKS 内でルーティング面を切り分ける
- WAF は両系統で適用

## 診断設定 / ロック

- App Gateway, Public IP, WAF Policy に診断設定を適用
- `enableResourceLock=true` の場合は各リソースに削除ロックを適用
