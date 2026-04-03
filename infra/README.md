# infra README

このディレクトリは、Azure インフラを Bicep でデプロイする実行基盤です。  
`main.sh` が `common.parameter.json` を読み込み、前処理で `.bicepparam` を動的生成して各リソースをデプロイします。

## ネットワーク構成図とフロー

### 構成図（基本構成）

![基本構成図](../docs/assets/Basic.png)

### 通信経路フロー（UDR）

```mermaid
flowchart LR
  AG["ApplicationGatewaySubnet<br/>10.189.129.0/24"]
  U["UserNodeSubnet<br/>10.189.128.0/24"]
  N["AgentNodeSubnet<br/>10.189.130.192/26"]
  M["MaintenanceSubnet<br/>10.189.131.0/29"]
  FW["Azure Firewall<br/>10.189.130.65"]
  NET["0.0.0.0/0 (Internet)"]

  RTFW["rt-dev-3pull-firewall<br/>udr-usernode-inbound<br/>udr-agentnode-inbound"]
  RTAKS["rt-dev-3pull-outbound-aks<br/>udr-appgw-return<br/>udr-internet-outbound"]
  RTM["rt-dev-3pull-outbound-maint<br/>udr-internet-outbound"]

  AG ---|"紐づけ"| RTFW
  U ---|"紐づけ"| RTAKS
  N ---|"紐づけ"| RTAKS
  M ---|"紐づけ"| RTM

  RTFW -->|"UserNodeSubnet 宛 / AgentNodeSubnet 宛<br/>next hop: 10.189.130.65"| FW
  RTAKS -->|"ApplicationGatewaySubnet 宛<br/>next hop: 10.189.130.65"| FW
  RTAKS -->|"0.0.0.0/0<br/>next hop: 10.189.130.65 または network.egressNextHopIp"| FW
  RTM -->|"0.0.0.0/0<br/>next hop: 10.189.130.65 または network.egressNextHopIp"| FW
  FW --> NET
```

### 通信制御フロー（NSG）

```mermaid
flowchart LR
  AG["ApplicationGatewaySubnet<br/>10.189.129.0/24"]
  U["UserNodeSubnet<br/>10.189.128.0/24<br/>NSG: usernode"]
  N["AgentNodeSubnet<br/>10.189.130.192/26<br/>NSG: agentnode"]
  P["PrivateEndpointSubnet<br/>10.189.130.128/26<br/>NSG: pep"]
  M["MaintenanceSubnet<br/>10.189.131.0/29<br/>NSG: maint"]
  B["AzureBastionSubnet<br/>10.189.130.0/26"]
  ACT["ActionGroup"]

  AG -->|"TCP 8080,3000,3080 許可"| U
  AG -->|"TCP 8080,3000,3080 許可"| N
  U -->|"TCP 443,4443 許可"| U
  U -->|"TCP 443,4443 許可"| N
  N -->|"TCP 443,4443 許可"| U
  N -->|"TCP 443,4443 許可"| N
  M -->|"Any 許可"| U
  M -->|"Any 許可"| N
  U -->|"Any 許可"| P
  N -->|"Any 許可"| P
  M -->|"Any 許可"| P
  ACT -->|"TCP 8080 許可"| U
  ACT -->|"TCP 8080 許可"| N
  B -->|"TCP 22,3389 許可"| M
```

### 構成図（ハブ&スポーク構成）

![ハブ&スポーク構成図](../docs/assets/Hubspo.png)

### 通信経路フロー（UDR）

```mermaid
flowchart LR
  AG["ApplicationGatewaySubnet<br/>10.189.129.0/24"]
  U["UserNodeSubnet<br/>10.189.128.0/24"]
  N["AgentNodeSubnet<br/>10.189.130.128/26"]
  M["MaintenanceSubnet<br/>10.189.130.192/29"]
  FW["Azure Firewall (Spoke)<br/>10.189.130.1"]
  HUB["Hub Egress Firewall<br/>10.47.80.10"]

  RTFW["rt-hubspo-3pull-firewall<br/>udr-usernode-inbound<br/>udr-agentnode-inbound"]
  RTAKS["rt-hubspo-3pull-outbound-aks<br/>udr-appgw-return<br/>udr-internet-outbound"]
  RTM["rt-hubspo-3pull-outbound-maint<br/>udr-internet-outbound"]

  AG ---|"紐づけ"| RTFW
  U ---|"紐づけ"| RTAKS
  N ---|"紐づけ"| RTAKS
  M ---|"紐づけ"| RTM

  RTFW -->|"UserNodeSubnet / AgentNodeSubnet 宛<br/>next hop: 10.189.130.1"| FW
  RTAKS -->|"ApplicationGatewaySubnet 宛 (udr-appgw-return)<br/>next hop: 10.189.130.1"| FW
  RTAKS -->|"0.0.0.0/0 (udr-internet-outbound)<br/>next hop: 10.47.80.10"| HUB
  RTM -->|"0.0.0.0/0 (udr-internet-outbound)<br/>next hop: 10.47.80.10"| HUB
```

### 通信制御フロー（NSG）

```mermaid
flowchart LR
  AG["ApplicationGatewaySubnet<br/>10.189.129.0/24"]
  U["UserNodeSubnet<br/>10.189.128.0/24<br/>NSG: nsg-hubspo-3pull-usernode"]
  N["AgentNodeSubnet<br/>10.189.130.128/26<br/>NSG: nsg-hubspo-3pull-agentnode"]
  P["PrivateEndpointSubnet<br/>10.189.130.64/26<br/>NSG: nsg-hubspo-3pull-pep"]
  M["MaintenanceSubnet<br/>10.189.130.192/29<br/>NSG: nsg-hubspo-3pull-maint"]
  B["Hub Bastion / Jump Source<br/>10.47.80.20"]
  ACT["ActionGroup"]

  AG -->|"TCP 8080,3000,3080 許可"| U
  AG -->|"TCP 8080,3000,3080 許可"| N
  U -->|"TCP 443,4443 許可"| U
  U -->|"TCP 443,4443 許可"| N
  N -->|"TCP 443,4443 許可"| U
  N -->|"TCP 443,4443 許可"| N
  M -->|"Any 許可"| U
  M -->|"Any 許可"| N
  U -->|"Any 許可"| P
  N -->|"Any 許可"| P
  M -->|"Any 許可"| P
  ACT -->|"TCP 8080 許可"| U
  ACT -->|"TCP 8080 許可"| N
  B -->|"TCP 22,3389 許可"| M
```

### 構成図（低遅延用 AppGW オプション構成）

![低遅延用 AppGW オプション構成図](../docs/assets/LowLatencyOption.png)

### 通信経路フロー（UDR）

```mermaid
flowchart LR
  AG["ApplicationGatewaySubnet<br/>10.189.129.0/24"]
  AGLL["ApplicationGatewayLowLatencySubnet<br/>10.189.130.0/24"]
  U["UserNodeSubnet<br/>10.189.128.0/24"]
  N["AgentNodeSubnet<br/>10.189.131.192/26"]
  M["MaintenanceSubnet<br/>10.189.132.0/29"]
  FW["Azure Firewall<br/>10.189.131.65"]
  NET["0.0.0.0/0 (Internet)"]

  RTFW["rt-stg-sun3pull-firewall<br/>udr-usernode-inbound<br/>udr-agentnode-inbound"]
  RTAKS["rt-stg-sun3pull-outbound-aks<br/>udr-appgw-return<br/>udr-internet-outbound"]
  RTM["rt-stg-sun3pull-outbound-maint<br/>udr-internet-outbound"]
  RTNONE["Route Table<br/>Not Attached"]

  AG ---|"紐づけ"| RTFW
  AGLL -.->|"UDR 未紐づけ"| RTNONE
  U ---|"紐づけ"| RTAKS
  N ---|"紐づけ"| RTAKS
  M ---|"紐づけ"| RTM

  RTFW -->|"UserNodeSubnet / AgentNodeSubnet 宛<br/>next hop: 10.189.131.65"| FW
  RTAKS -->|"ApplicationGatewaySubnet 宛 (udr-appgw-return)<br/>next hop: 10.189.131.65"| FW
  RTAKS -->|"0.0.0.0/0 (udr-internet-outbound)<br/>next hop: 10.189.131.65"| FW
  RTM -->|"0.0.0.0/0 (udr-internet-outbound)<br/>next hop: 10.189.131.65"| FW
  FW --> NET
```

### 通信制御フロー（NSG）

```mermaid
flowchart LR
  AG["ApplicationGatewaySubnet<br/>10.189.129.0/24"]
  AGLL["ApplicationGatewayLowLatencySubnet<br/>10.189.130.0/24"]
  U["UserNodeSubnet<br/>10.189.128.0/24<br/>NSG: nsg-stg-sun3pull-usernode"]
  N["AgentNodeSubnet<br/>10.189.131.192/26<br/>NSG: nsg-stg-sun3pull-agentnode"]
  P["PrivateEndpointSubnet<br/>10.189.131.128/26<br/>NSG: nsg-stg-sun3pull-pep"]
  M["MaintenanceSubnet<br/>10.189.132.0/29<br/>NSG: nsg-stg-sun3pull-maint"]
  B["AzureBastionSubnet<br/>10.189.131.0/26"]
  ACT["ActionGroup"]

  AG -->|"TCP 8080,3000,3080 許可"| U
  AG -->|"TCP 8080,3000,3080 許可"| N
  AGLL -->|"TCP 8080,3000,3080 許可"| U
  AGLL -->|"TCP 8080,3000,3080 許可"| N
  U -->|"TCP 443,4443 許可"| U
  U -->|"TCP 443,4443 許可"| N
  N -->|"TCP 443,4443 許可"| U
  N -->|"TCP 443,4443 許可"| N
  M -->|"Any 許可"| U
  M -->|"Any 許可"| N
  U -->|"Any 許可"| P
  N -->|"Any 許可"| P
  M -->|"Any 許可"| P
  ACT -->|"TCP 8080 許可"| U
  ACT -->|"TCP 8080 許可"| N
  B -->|"TCP 22,3389 許可"| M
```

ネットワーク構成の設計は [docs/infra/network.md](../docs/infra/network.md) を参照してください。

## このフォルダ配下の説明

- `main.sh`
  - エントリーポイント。パラメータ生成とデプロイを順序制御します。
- `common.parameter.json`
  - 共通パラメータと、どのリソースをデプロイ対象にするか（実行可否）を管理します。
  - `common` / `logAnalytics` / `network` / `aks` / `keyVault` / `serviceBus` / `storage` / `sqlDatabase` / `redis` / `postgres` / `cosno` / `resourceToggles` の親オブジェクトで分類しています。
- `bicep/`
  - リソース単位の Bicep 本体。
- `scripts/`
  - `main.sh` から呼び出される前処理スクリプト（`.bicepparam` 生成）。
- `config/`
  - 原則、ユーザーが変更しない固定定義。
- `params/`
  - 動的生成される `.bicepparam` / `*-meta.json` の出力先。

## 前提要件

- Azure CLI (`az`) が利用できること
- Python 3 が利用できること

## 実行前の準備（共通パラメータ）

デプロイ前に `infra/common.parameter.json` を環境に合わせて設定してください。

### common.location

Azure の有効なリージョン名を指定します。  
リージョン一覧確認:

```bash
az account list-locations --query "[].name" -o tsv
```

### common.environmentName

`prod` / `stg` / `dev` などの環境名です。任意の文字列を指定できます。リソース名とタグに反映されます。

### common.systemName

システム名です。リソース名とタグに反映されます。

### common.enableResourceLock

リソース削除ロックを有効化するかどうかを指定します。

- `true`（デフォルト）: すべての対象リソースに削除ロックを適用
- `false`: 削除ロックを適用しない（検証環境での作成/削除を優先する場合）

### logAnalytics.dailyQuotaGb

Log Analytics Workspace の日次データ取り込み上限を指定します。  
単位は **GB/日**（1 日あたりの上限）です。

- `-1`（デフォルト）: 無制限
- `0` 以上の整数: 指定した GB/日 を上限として適用

設定例:

```json
"logAnalytics": {
  "dailyQuotaGb": 10
}
```

注意:

- 小数は指定できません（整数のみ）。
- `-1` 未満は無効値です。

### network.enableFirewallIdps

IDS/IPS を有効にするかどうかを指定します。  
`true` の場合は **Firewall SKU が Premium** になり、IDS/IPS を有効化します。  
`false` の場合は **Firewall SKU が Standard** になります。

- `false`（デフォルト）
- 注意: `true`（Premium）は比較的高額な料金が発生するため、コスト影響を確認してから有効化してください。

### network.enableGatewayRoutePropagation

ルートテーブルのゲートウェイルート伝搬（BGP ルート伝搬）を有効化するかどうかを指定します。

- `false`（デフォルト）: 無効
- `true`: 有効

推奨は `false`（無効）です。  
理由:

- UDR の next hop を常に優先し、意図しない BGP 経路混入を防止しやすくなるため
- ハブ側 ExpressRoute / VPN Gateway からの経路広告による予期せぬ経路変更を避けやすくなるため
- 障害時の経路切り分けを単純化しやすくなるため

### network.enableCentralizedPrivateDns

Private Endpoint 向け Private DNS ゾーンを、この環境で作成するかどうかの設計方針を指定します。

ここでいう「集約 DNS」は、企業ポリシーによりハブ＆スポーク構成で
Private DNS ゾーンをハブ側（共通基盤側）に集約して一元管理する運用を指します。
各スポーク環境ごとにゾーンを個別作成せず、共通の DNS 基盤を参照する前提です。

- `false`（デフォルト）: 集約 DNS なし。各環境側で Private DNS ゾーンを作成して利用
- `true`: 集約 DNS あり。各環境側でのゾーン作成をスキップし、ハブ側などの集約 DNS で管理されたゾーンを利用

### network.enableLowLatencyApplicationGatewaySubnet

低遅延系エンドポイント用に、通常系とは別の `ApplicationGatewayLowLatencySubnet` を作成するかどうかを指定します。  
通常系 `ApplicationGatewaySubnet` / 低遅延系 `ApplicationGatewayLowLatencySubnet` はともに `/24` で作成されます。

- `false`（デフォルト）: 低遅延用サブネットを作成しない
- `true`: `ApplicationGatewayLowLatencySubnet` を作成し、低遅延用 AppGW 構成を有効化

注意:

- 音声データ配信やリアルタイム処理など、同時接続数が増えるワークロードで Firewall 経由がボトルネックになり得る場合に有効です。
- 通常系は Firewall 経由（検査・集中制御）、低遅延系は AppGW 直通（遅延最小化）という用途分離を前提に運用してください。
- 低遅延用サブネットは UDR/NSG を紐づけない設計です。そのため、入口側は WAF/AppGW で制御し、公開 API を限定する前提です。

### network.enableDdosProtection

DDoS Protection の有効/無効を指定します。  
`true` の場合は、DDoS Protection Plan を（既存利用または新規作成して）VNET に適用します。  
`false` の場合は、DDoS Protection Plan の作成をスキップし、VNET への DDoS Protection 適用もしません。

- `false`（デフォルト）
- 注意: `true` にすると DDoS Protection Plan の利用料金が発生し、比較的高額になるため、事前に費用を確認してください。

### network.ddosProtectionPlanId

`network.enableDdosProtection=true` の場合に利用される設定です。  
未指定の場合は、`ddos-[environmentName]-[systemName]` の DDoS Protection Plan を新規作成して VNET に適用します。  
企業ポリシー等により既存の保護プランを利用する場合は、そのリソース ID を指定してください。  
入力例: `/subscriptions/<subscriptionId>/resourceGroups/<resourceGroupName>/providers/Microsoft.Network/ddosProtectionPlans/<ddosPlanName>`

### network.vnetAddressPrefixes

VNET のアドレス空間です。サブネットを動的計算するため、必要な最小レンジは `network.sharedBastionIp` と `network.enableLowLatencyApplicationGatewaySubnet` の組み合わせで変わります。

- `network.sharedBastionIp` 指定あり かつ `network.enableLowLatencyApplicationGatewaySubnet=false`
  - `/24` が 3 つ分
  - 連続するレンジを確保できる場合は、`/23` が 1 つ分 + `/24` が 1 つ分、または `/22` が 1 つ分（`/24` 3 つ分相当）
- `network.sharedBastionIp` 未指定 かつ `network.enableLowLatencyApplicationGatewaySubnet=false`
  - `/24` が 4 つ分
  - または `/22` が 1 つ分（`/24` 4 つ分相当）
- `network.sharedBastionIp` 指定あり かつ `network.enableLowLatencyApplicationGatewaySubnet=true`
  - `/24` が 4 つ分
  - または `/22` が 1 つ分（`/24` 4 つ分相当）
- `network.sharedBastionIp` 未指定 かつ `network.enableLowLatencyApplicationGatewaySubnet=true`
  - `/24` が 5 つ分
  - または `/21` が 1 つ分（`/24` 5 つ分相当）

### network.vnetDnsServers

VNET が参照する DNS リゾルバです（IP アドレス配列）。

- 未指定（`[]`）: Azure 提供 DNS を利用
- 指定あり: 指定した DNS サーバーを利用

ハブ&スポーク構成で集約 DNS を利用する場合は、ハブ側 Firewall などの DNS プロキシ/リゾルバの **プライベート IP** を指定してください。  
例:

```json
"vnetDnsServers": ["10.10.0.4"]
```

### network.egressNextHopIp

AKS ノード系サブネットやメンテナンス VM サブネットからのアウトバウンド経路を制御するための設定です。  
基本（未指定）の場合は、新規作成した Firewall のプライベート IP を next hop とするユーザー定義ルート（UDR）を作成します。  
企業ポリシー上、ハブ＆スポーク構成で VNET ピアリングされた集約アウトバウンド経路を使う必要がある場合は、この値に IP を指定することで UDR の宛先（next hop）をその IP に書き換えます。
ルートテーブルは `outbound-aks` / `outbound-maint` に分離され、ゲートウェイルート伝搬（BGP ルート伝搬）の有効/無効は `network.enableGatewayRoutePropagation` で制御します（推奨は無効）。

### network.sharedBastionIp

メンテナンス VM 用サブネット（`MaintenanceSubnet`）に対して通信を許可する送信元を指定します。  
基本（未指定）の場合は、新規作成される `AzureBastionSubnet` からの通信のみ許可します。  
企業ポリシー上、ハブ＆スポーク構成で VNET ピアリングされた集約踏み台サーバを利用する必要がある場合は、この値に IP または CIDR（例: `10.0.10.0/24`）を指定することで NSG の許可送信元を書き換えます。  
許可される通信は SSH（22）と RDP（3389）です。

注記:

- `AzureBastionSubnet` は作成しますが、Azure Bastion サービス本体は自動作成しません。
- 企業ポリシーによって Azure Bastion が利用不可のケースもあるため、Bastion または踏み台サーバは要件に合わせて手動で作成してください。

### aks.userPoolVmSize

Azure Kubernetes Service「ユーザープール」（アプリ用ノード）の VM サイズです。  
アプリの同時実行数、CPU/メモリ要件、コストに直接影響します。

- 例: `Standard_D4s_v4`（中規模）
- 目安:
  - 小規模検証: `Standard_D2s_v4`
  - 本番寄り: `Standard_D4s_v4` 以上

### aks.userPoolCount / aks.userPoolMinCount / aks.userPoolMaxCount

Azure Kubernetes Service「ユーザープール」（アプリ用ノード）の ノード台数です。
オートスケーリング時の下限/上限もここで指定します。

- `aks.userPoolCount`: 初期ノード数
- `aks.userPoolMinCount`: 自動縮退時の最小ノード数
- `aks.userPoolMaxCount`: 自動拡張時の最大ノード数

必須条件:

- `aks.userPoolMinCount <= aks.userPoolCount <= aks.userPoolMaxCount`

### aks.userPoolLabel

Azure Kubernetes Service「ユーザープール」（アプリ用ノード）の ノードラベル値です。  
Azure Kubernetes Service では `pool=<この値>` のラベルがノードに付き、Pod の `nodeSelector` / `affinity` で配置先制御に使います。

- 例: `user`, `batch`, `api`

### aks.podCidr

Azure Kubernetes Service の Pod に割り当てる IP 範囲（CIDR）です。  
Overlay CNI では VNET サブネットとは別空間で管理されます。  
ただし、AKS マニフェストやネットワーク設計によって外部との通信経路が成立する構成では、重複 IP が競合する可能性があります。  
そのため、下記のような接続がある場合は、競合しないレンジから採番することを推奨します。  

- この AKS から VNET ピアリング先の別 VNET（別 AKS クラスタを含む）へ通信する場合
- この AKS から VPN/ExpressRoute 経由でオンプレミス環境へ通信する場合
- 逆に、別 VNET やオンプレミス側からこの AKS（Pod 宛）へ到達させる場合

- 例: `10.189.0.0/17`
- 形式: `x.x.x.x/xx`

### aks.serviceCidr

Kubernetes Service（ClusterIP）用の IP 範囲（CIDR）です。  
`dnsServiceIP` はこのレンジ内の 10 番目の利用可能 IP を自動設定します。

- 例: `10.47.0.0/24`
- 形式: `x.x.x.x/xx`
- 注意:
  - `network.vnetAddressPrefixes` と重複不可
  - `aks.podCidr` と重複不可
- 利用可能 IP が 10 個以上必要

### Key Vault / Service Bus / Storage の Workload Identity RBAC

`keyVault` / `serviceBus` / `storage` をデプロイする場合、各リソースの Managed Identity RBAC は自動判定で適用します。

- 判定条件:
  - 対象リソースの `resourceToggles` が `true`
  - 必要な Managed Identity が Azure 上に実在する
- 条件を満たす場合のみ RBAC を作成し、満たさない場合は RBAC 作成をスキップします。
- Key Vault では `api` / `worker` に `Key Vault Secrets User` に加えて `Key Vault Crypto User` も付与します。
  Azure SQL Always Encrypted で Azure Key Vault のキーを利用する前提です。

### AGIC / Ingress / KEDA の現状

- AGIC は AKS addon ではなく Helm bootstrap script で導入する前提です
- `infra/main.sh` の post フェーズで、以下を生成します
  - `scripts/init/agicController/deploy.sh`
  - `scripts/init/kedaController/deploy.sh`
  - `k8s/charts/frontend/values.yaml`
  - `k8s/charts/backend/values.yaml`
- AGIC 用 Managed Identity は通常系 / 低遅延系で分離し、App Gateway 更新権限は `main.application-gateway-rbac.bicep` で付与します
- AGIC / KEDA / backend workloads 用 federated credential は `main.federated-credential.bicep` で作成します
- backend / frontend の Ingress manifest 自体は app chart 側で管理します
  - backend は通常系 / 低遅延系の 2 系統
  - frontend は通常系のみ
- backend chart は KEDA 用の `TriggerAuthentication` / `ScaledObject` を持ち、values 生成時に `keda.workloadIdentity.clientId` を自動反映します
- backend workloads が Application Insights へ Entra 認証で telemetry を送れるよう、`main.application-insights-rbac.bicep` で API / worker / schedulers MI に `Monitoring Metrics Publisher` を付与します
- AGIC 用 namespace はアプリ namespace と分離可能で、`ingress` 専用 namespace を使う前提で bootstrap できます
- 公開方針は以下を前提にします
  - 通常系 / 低遅延系はドメインで分離する
  - 低遅延系は限定 API のみを公開する
  - frontend は通常系 App Gateway のみで公開する
  - TLS 終端は App Gateway 側で管理する

### sqlDatabase.skuTier

Azure SQL Database の価格レベルです。

- デフォルト: `Basic`
- 主な選択肢: `Basic` / `Standard` / `Premium` / `GeneralPurpose` / `BusinessCritical` / `Hyperscale`

サンプルアプリの初期構成では `Basic` を既定とし、検証用途で十分な最小構成を優先します。

### sqlDatabase.skuName

Azure SQL Database の SKU 名です。

- デフォルト: `Basic`

`skuTier` と整合する値を指定してください。初期構成では `skuTier=Basic`, `skuName=Basic` を前提にしています。

### sqlDatabase.maxSizeGb

Azure SQL Database の最大サイズ (GiB) です。

- デフォルト: `2`

サンプルアプリ用途では 2 GiB を既定とし、必要に応じて拡張します。

### sqlDatabase.zoneRedundant

Azure SQL Database の zone redundancy を有効化するかどうかです。

- `false`（デフォルト）: 無効
- `true`: 有効

可用性要件とコストを見ながら有効化してください。サンプルアプリの初期構成では無効を既定とします。

### sqlDatabase.entraAdminLogin

Azure SQL Server の Microsoft Entra administrator に設定する主体のログイン名です。

設定可能な主体:

- Entra ユーザー
- Entra グループ

推奨:

- 個人ユーザーではなく Entra グループを指定してください。

例:

- ユーザー: `3pull-admin@example.com`
- グループ: `sql-admins-dev-3pull`

確認例:

```bash
az ad user show \
  --id 3pull-admin@example.com \
  --query "{login:userPrincipalName, objectId:id}"
```

```bash
az ad group show \
  --group sql-admins-dev-3pull \
  --query "{login:displayName, objectId:id}"
```

### sqlDatabase.entraAdminObjectId

`sqlDatabase.entraAdminLogin` に対応する Entra object ID です。  
Azure SQL Server の Microsoft Entra administrator 設定に利用します。

設定可能な主体:

- Entra ユーザーの object ID
- Entra グループの object ID

注意:

- ここで指定するのは Managed Identity ではありません。
- runtime 用 / migration 用の Managed Identity は、Azure SQL Database 内で `CREATE USER ... FROM EXTERNAL PROVIDER` して利用する別の principal です。
- Azure SQL Server の Entra administrator には、通常はユーザーまたはグループを設定します。

### SQL Database デプロイ時の補足

Azure SQL Server は Microsoft Entra admin を標準の運用経路としつつ、bootstrap / 緊急時用に SQL 管理者ログインも保持します。  
そのため `resourceToggles.sqlDatabase=true` でデプロイする場合は、実行時に以下の環境変数を指定してください。

```bash
SQL_ADMIN_LOGIN='sqladmin' \
SQL_ADMIN_PASSWORD='YourStrongPassword!' \
bash infra/main.sh
```

- `SQL_ADMIN_LOGIN`
  - SQL Server 作成時の一時的な管理者ログイン名
- `SQL_ADMIN_PASSWORD`
  - SQL Server 作成時の一時的な管理者パスワード

通常運用のアプリ接続は Microsoft Entra 認証を前提とし、SQL 認証は bootstrap や緊急時対応のために保持します。

### redis.skuName

Azure Managed Redis の SKU 名です。

- デフォルト: `Balanced_B0`

初期実装では検証向けの最小構成を既定とし、環境ごとに上書き可能にしています。

`az redisenterprise` は Azure CLI extension のコマンドです。未導入の場合は先に extension を追加してください。

```bash
az extension add --name redisenterprise
```

利用可能な SKU 候補は `az redisenterprise create --help` の `Accepted values` で確認できます。

```bash
az redisenterprise create --help
```

`--sku` 周辺だけを抜き出して確認したい場合:

```bash
az redisenterprise create --help | grep -A 20 -- '--sku'
```

`skuName` の見方:

- `Balanced_*`
  - 汎用バランス型
  - 初期導入ではまずこの系列を優先
- `ComputeOptimized_*`
  - CPU 寄り
- `MemoryOptimized_*`
  - メモリ寄り
- `FlashOptimized_*`
  - Flash ストレージ寄り
- `Enterprise_*`
  - Enterprise 系
  - capacity の概念あり
- `EnterpriseFlash_*`
  - Enterprise Flash 系
  - capacity の概念あり

初期構成では、まず次の順で検討してください。

1. 検証用途なら `Balanced_B0`
2. CPU 寄り要件が強ければ `ComputeOptimized_*`
3. メモリ寄り要件が強ければ `MemoryOptimized_*`
4. Enterprise / EnterpriseFlash 系は、必要性が明確な場合のみ選ぶ

補足:

- `Enterprise_*` / `EnterpriseFlash_*` 以外では capacity は指定しません。
- 利用可能 SKU はリージョンや Azure 側更新で変わり得るため、実際の候補は都度 `az redisenterprise create --help` で確認してください。

### redis.highAvailabilityEnabled

Azure Managed Redis の高可用性構成を有効化するかどうかです。

- `true`（デフォルト）: 有効
- `false`: 無効

### postgres.enableZoneRedundantHa

Azure Database for PostgreSQL Flexible Server のゾーン冗長HA（ZoneRedundant）を有効化するかどうかを指定します。

- `false`（デフォルト）: HA無効（`highAvailability.mode=Disabled`）
- `true`: HA有効（`highAvailability.mode=ZoneRedundant`）

注意:

- `true` の場合、リージョン/AZのサポート可否に依存します。
- `true` の場合、`postgres.skuTier=Burstable` は利用できません（HA 非対応）。
  - HA を有効にする場合は `postgres.skuTier` を `GeneralPurpose` または `MemoryOptimized` に設定してください。
- `true` はコスト増となるため、可用性要件と費用を確認して設定してください。

### postgres.skuTier

Azure Database for PostgreSQL Flexible Server の価格レベル（SKU Tier）です。

- デフォルト: `Burstable`
- 主な選択肢: `Burstable` / `GeneralPurpose` / `MemoryOptimized`

### postgres.skuName

Azure Database for PostgreSQL Flexible Server のコンピューティングサイズです。

- デフォルト: `Standard_B2s`
- 例（デフォルト）: `Standard_B2s`（2 vCore / 4 GiB メモリ / SKU仕様上の最大 IOPS 1280）

`skuName` の候補は Azure CLI で確認できます。

```bash
az postgres flexible-server list-skus \
  --location <common.location> \
  -o table
```

例:

```bash
az postgres flexible-server list-skus --location japaneast -o table
```

`skuTier` と `skuName` の組み合わせ例（`Burstable`）:

- `Burstable` + `Standard_B1ms`
- `Burstable` + `Standard_B2s`（デフォルト）
- `Burstable` + `Standard_B2ms`

### postgres.storageSizeGB

Azure Database for PostgreSQL Flexible Server のストレージ容量（GiB）です。

- デフォルト: `32`

### postgres.enableStorageAutoGrow

Azure Database for PostgreSQL Flexible Server のストレージ自動拡張を有効化するかどうかを指定します。

- `false`（デフォルト）: 無効
- `true`: 有効

### postgres.enableGeoRedundantBackup

Azure Database for PostgreSQL Flexible Server の Geo 冗長バックアップを有効化するかどうかを指定します。

- `false`（デフォルト）: 無効（同一リージョン内のバックアップ）
- `true`: 有効（別リージョンにもバックアップを複製）

注意:

- `true` はコスト増となるため、DR 要件と費用を確認して設定してください。

### postgres.backupRetentionDays

Azure Database for PostgreSQL Flexible Server の PITR 保持日数です。

- デフォルト: `7`
- 設定可能範囲: `7` 〜 `35`（整数）

### postgres.enableCustomMaintenanceWindow

Azure Database for PostgreSQL Flexible Server のメンテナンスウィンドウをカスタム指定するかどうかです。

- `false`（デフォルト）: システム管理スケジュールを利用
- `true`: `postgres.maintenanceWindow` の値を利用して固定化

### postgres.maintenanceWindow

`postgres.enableCustomMaintenanceWindow=true` の場合に利用するメンテナンスウィンドウ設定です。

- `dayOfWeek`: `0`〜`6`（曜日）
- `startHour`: `0`〜`23`（UTC）
- `startMinute`: `0`〜`59`（UTC）

### cosno.backupPolicyType

Cosmos DB のバックアップ方式を指定します。

- `Periodic`（デフォルト）: 定期バックアップ
- `Continuous`: 連続バックアップ（PITR）

### cosno.throughputMode

Cosmos DB（NoSQL API）のスループット方式を指定します。

- デフォルト: `Serverless`
- 選択肢: `Manual` / `Autoscale` / `Serverless`

### cosno.manualThroughputRu

`cosno.throughputMode=Manual` の場合に利用する RU/s です。

- デフォルト: `400`
- 推奨下限: `400`

### cosno.autoscaleMaxThroughputRu

`cosno.throughputMode=Autoscale` の場合に利用する最大 RU/s です。

- デフォルト: `1000`
- 推奨下限: `1000`

### cosno.periodicBackupIntervalInMinutes

`cosno.backupPolicyType=Periodic` の場合に利用するバックアップ間隔（分）です。

- デフォルト: `240`（4時間）
- 設定範囲: `60`〜`1440`

### cosno.periodicBackupRetentionIntervalInHours

`cosno.backupPolicyType=Periodic` の場合に利用するバックアップ保持時間（時間）です。

- デフォルト: `8`（2世代相当）
- 設定範囲: `8`〜`720`
- 注意: 値は `periodicBackupIntervalInMinutes` の2倍以上が必要です。

### cosno.periodicBackupStorageRedundancy

`cosno.backupPolicyType=Periodic` の場合に利用するバックアップ保存先冗長性です。

- デフォルト: `Geo`
- 主な選択肢: `Geo` / `Local` / `Zone`

### cosno.continuousBackupTier

`cosno.backupPolicyType=Continuous` の場合に利用する連続バックアップ層です。

- デフォルト: `Continuous30Days`
- 選択肢: `Continuous7Days` / `Continuous30Days`

### cosno.failoverRegions

Cosmos DB の DR 用セカンダリリージョン一覧です（優先順）。

- デフォルト: `[]`（単一リージョン運用）
- 例: `["japanwest"]`

### cosno.enableAutomaticFailover

Cosmos DB の自動フェールオーバーを有効化するかどうかです。

- デフォルト: `false`
- `true` の場合、`cosno.failoverRegions` に1件以上のリージョン設定が必要です。

### cosno.enableMultipleWriteLocations

Cosmos DB の複数リージョン書き込み（マルチマスター）を有効化するかどうかです。

- デフォルト: `false`

### cosno.consistencyLevel

Cosmos DB の既定整合性レベルです。

- デフォルト: `Session`
- 選択肢: `Strong` / `BoundedStaleness` / `Session` / `ConsistentPrefix` / `Eventual`

### cosno.disableLocalAuth

Cosmos DB のキー/SAS などローカル認証を無効化するかどうかです。

- デフォルト: `false`（ローカル認証有効）
- `true`: ローカル認証を無効化（Entra/RBAC 中心運用）

### cosno.disableKeyBasedMetadataWriteAccess

Cosmos DB のキーによるメタデータ書き込みを無効化するかどうかです。

- デフォルト: `false`
- `true`: キーベースのメタデータ更新を制限

### resourceToggles

リソース単位の実行可否です。

- `logAnalytics`
- `applicationInsights`
- `virtualNetwork`
- `subnets`
  - `subnets`, `route-tables`, `nsgs`, `subnet-attachments` を一括制御
- `firewall`
- `managedIds`
- `applicationGateway`
- `aks`
- `acr`
- `keyVault`
- `serviceBus`
- `storage`
- `sqlDatabase`
- `redis`
- `maintenanceVm`
- `postgresDatabase`
- `cosmosDatabase`
- `agicController`
- `kedaController`

## ネットワーク構成ドキュメント

サブネット構成やルート/NSG の設計方針は [docs/infra/network.md](../docs/infra/network.md) を参照してください。

## デプロイ手順

### Azureログイン

```bash
az login
```

### 操作対象サブスクリプションの設定

```bash
az account set --subscription {SubscriptionId}
az account show
```

### デプロイ

```bash
cd infra
SQL_ADMIN_LOGIN='sqladmin' \
SQL_ADMIN_PASSWORD='YourStrongPassword!' \
MAINT_VM_ADMIN_LOGIN='maintadmin' \
MAINT_VM_ADMIN_PASSWORD='YourStrongPassword!' \
./main.sh --what-if

SQL_ADMIN_LOGIN='sqladmin' \
SQL_ADMIN_PASSWORD='YourStrongPassword!' \
MAINT_VM_ADMIN_LOGIN='maintadmin' \
MAINT_VM_ADMIN_PASSWORD='YourStrongPassword!' \
./main.sh
```

`resourceToggles.postgresDatabase=true` で PostgreSQL Flexible Server もデプロイする場合のみ、追加で `POSTGRES_ADMIN_PASSWORD` を指定してください。

### デプロイの流れ

- monitor
  - Log Analytics Workspace
  - Application Insights
- network
  - Virtual Network
  - Subnets（作成のみ）
  - Firewall
  - Route Tables
  - NSGs
  - Subnet Attachments（RouteTable/NSG紐づけ）
- service
  - Managed IDs
  - Application Gateway
  - Application Gateway（Low Latency, `network.enableLowLatencyApplicationGatewaySubnet=true` の場合）
  - Application Gateway RBAC（AGIC 用 Managed Identity に App Gateway 更新権限を付与）
  - AKS
  - Federated Credential（`resourceToggles.aks=true` かつ必要な Managed Identity が存在し、`infra/config/federated-credential.json` の `enabled=true` の場合）
  - ACR（ACR RG スコープで AKS をアタッチ）
  - Key Vault
  - Service Bus
  - Storage Account
  - Azure SQL Database
  - Azure Managed Redis
  - Maintenance VM
  - PostgreSQL Flexible Server
  - Cosmos DB (NoSQL)
- post
  - AGIC コントローラ導入（`resourceToggles.agicController=true` かつ Federated Credential が作成済み かつ AKS が存在する場合のみ）
  - KEDA コントローラ導入（`resourceToggles.kedaController=true` かつ Federated Credential が作成済み かつ AKS が存在する場合のみ）
  - frontend Helm values 生成（`infra/config/frontend-values.template.yaml` から `k8s/charts/frontend/values.yaml` を生成）
  - backend Helm values 生成（`infra/config/backend-values.template.yaml` から `k8s/charts/backend/values.yaml` を生成）
  - IP rate limit ops 用 env 生成（`scripts/ops/ip-rate-limit/generated.env.sh`）

### post フェーズで現在生成・整備されるもの

- `scripts/init/agicController/deploy.sh`
  - AGIC standard / low-latency を Helm で導入する bootstrap script
- `scripts/init/kedaController/deploy.sh`
  - KEDA controller を Helm で導入する bootstrap script
- `scripts/init/sql/param.conf`
  - SQL bootstrap 用の接続パラメータ
- `k8s/charts/frontend/values.yaml`
  - `infra/config/frontend-values.template.yaml` から生成する frontend chart 用 values
- `k8s/charts/backend/values.yaml`
  - `infra/config/backend-values.template.yaml` から生成する backend chart 用 values

補足:

- 現時点では `infra/main.sh` がインフラ作成に加えて bootstrap script / Helm values 生成まで担います。

## 出力ファイル（params/）

- `log-analytics.bicepparam`
- `application-insights.bicepparam`
- `virtual-network.bicepparam`
- `subnets.bicepparam`
- `firewall.bicepparam`
- `route-tables.bicepparam`
- `nsgs.bicepparam`
- `subnet-attachments.bicepparam`
- `managed-ids.bicepparam`
- `application-gateway.bicepparam`
- `application-gateway-rbac.bicepparam`
- `acr.bicepparam`
- `key-vault.bicepparam`
- `service-bus.bicepparam`
- `storage.bicepparam`
- `redis-managed.bicepparam`
- `cosmos-database.bicepparam`
- `postgres-database.bicepparam`
- `aks.bicepparam`
- `maintenance-vm.bicepparam`

補足:

- `params/` 配下は生成物として `.gitignore` 対象です（`.gitkeep` を除く）。

## メンテVM作成後の個別手順

### 目的

メンテVMへの安全な運用アクセスを有効化し、運用作業に必要な CLI を利用可能にします。

### 1. Entra ID ログイン拡張の有効化

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group rg-[environmentName]-[systemName]-maint \
    --vm-name vm-[environmentName]-[systemName]-maint
```

対象アカウントに以下いずれかの RBAC ロール付与が必要です。

- 仮想マシン管理者ログイン
- 仮想マシンユーザーログイン

### 2. メンテVMへログイン

```bash
az login
az ssh vm -n vm-[environmentName]-[systemName]-maint -g rg-[environmentName]-[systemName]-maint
```

### 3. メンテVM内で Azure CLI を利用する場合

```shell
sudo apt-get update
sudo apt-get install apt-transport-https ca-certificates curl gnupg lsb-release

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
sudo apt-get install azure-cli
```

- メンテVM仕様の詳細: [docs/infra/maint-vm.md](../docs/infra/maint-vm.md)
