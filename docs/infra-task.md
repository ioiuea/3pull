# Infra タスク整理

## Ingress 要件（確定）

### 1. コントローラ方式

- AGIC は Helm 管理へ統一する（AKS の `ingressApplicationGateway` addon は利用しない）。
- 通常系 App Gateway / 低遅延系 App Gateway 用に、AGIC を 2 リリースで運用する。

### 2. 公開方式

- 通常系/低遅延系はドメインで分離する。
- 低遅延系のサブドメインは `ll`（`low-latency` の略）を使う。
  - 例: `api.3pull.com`（通常系）
  - 例: `ll-api.3pull.com`（低遅延系）

### 3. Helm 管理方針

- Ingress は backend chart / frontend chart それぞれで管理する。
- Ingress 反映は app-deploy（Helm）ジョブで毎回実行する。

### 4. 低遅延系の適用範囲

- 低遅延系は限定 API のみ公開する。
- 切り替えは Ingress values の host/path で明示管理する。

### 5. TLS

- TLS 終端は App Gateway 側で管理する。

### 6. Frontend 公開

- frontend は通常系 App Gateway のみで公開する。
- 低遅延系 App Gateway では frontend を公開しない。

### 7. 監視・運用

- 通常系/低遅延系で監視・アラートを分離する。

## 既存 infra 実装との整合メモ

- 低遅延オプションは `network.enableLowLatencyApplicationGatewaySubnet` で切替済み。
- `ApplicationGatewayLowLatencySubnet` は作成可能だが、現状は UDR/NSG 非紐づけで運用する。
- 低遅延系 App Gateway は通常系とは別名で作成する（`agw-ll-*`）。

## AGIC Helm 統一方針（確定）

### 方針

- 既存の AKS addon AGIC と Helm AGIC の混在運用は行わず、AGIC は Helm 管理へ統一する。
- 通常系 App Gateway / 低遅延系 App Gateway それぞれに対して、AGIC を 2 リリースで運用する。

### 実施手順

1. AKS addon AGIC を無効化する
   - Bicep (`main.aks.bicep`) の `enableIngressApplicationGatewayAddon` は `false` 前提にする
   - 既存環境は `az aks disable-addons --addons ingress-appgw ...` を実施する
2. AGIC 用 Managed Identity を 2 つ作成する
   - `mi-<env>-<system>-agic-standard`
   - `mi-<env>-<system>-agic-lowlatency`
3. 各 Managed Identity に App Gateway 更新権限を付与する
   - 通常系 MI は通常系 App Gateway を更新可能にする
   - 低遅延系 MI は低遅延系 App Gateway を更新可能にする
4. AGIC 用 Workload Identity を構成する
   - ServiceAccount を AGIC 用に 2 つ作成する
   - `azure.workload.identity/client-id` annotation を設定する
   - 各 Managed Identity に federated credential を作成する
5. Helm で AGIC を 2 リリース導入する
   - `agic-standard`
     - `appgw.applicationGatewayID = <通常系 AppGW ID>`
     - `kubernetes.ingressClass = azure-application-gateway`
     - `serviceAccount.name = sa-agic-standard`
   - `agic-lowlatency`
     - `appgw.applicationGatewayID = <低遅延系 AppGW ID>`
     - `kubernetes.ingressClass = azure-application-gateway-low-latency`
     - `serviceAccount.name = sa-agic-lowlatency`
6. アプリ側 Ingress は IngressClass で振り分ける
   - backend:
     - 通常系 Ingress -> `azure-application-gateway`
     - 低遅延系 Ingress -> `azure-application-gateway-low-latency`（限定 API のみ）
   - frontend:
     - 通常系のみ

### 実装ステータス（2026-03-06 時点）

1. AKS addon AGIC を無効化する: 完了
   - `main.aks.bicep` は `enableIngressApplicationGatewayAddon=false` 前提
2. AGIC 用 Managed Identity を作成する: 完了
   - `mi-<env>-<system>-agic-standard`
   - `mi-<env>-<system>-agic-lowlatency`（低遅延オプション時）
3. App Gateway 更新権限を付与する: 完了
   - `main.application-gateway-rbac.bicep` で `AppGateway Contributor` を付与
4. AGIC 用 Workload Identity を構成する: 完了
   - federated credential は `main.federated-credential.bicep`
   - ServiceAccount/annotation は `infra/main.sh` の AGIC Helm で設定
5. Helm で AGIC を 2 リリース導入する: 完了
   - `resourceToggles.agicController=true` かつ `resourceToggles.federatedCredential=true` で実行
6. アプリ側 Ingress の振り分け: 完了
   - backend: standard + lowLatency
   - frontend: standard のみ

## KEDA / Workload Identity 整合メモ（現実装）

- KEDA コントローラ導入は `infra/main.sh`（`resourceToggles.kedaController=true`）で実施
- KEDA 用 MI はアプリ worker から分離済み
  - `mi-<env>-<system>-keda-operator`
- KEDA 用 federated credential は Bicep で作成
  - subject: `system:serviceaccount:<kedaNamespace>:<kedaOperatorServiceAccountName>`
- KEDA 用 ServiceAccount/annotation は `infra/main.sh` の KEDA Helm で設定
- backend chart 側の `keda.workloadIdentity.clientId` は values 生成時に keda-operator MI の clientId を埋め込み
- KEDA 実行条件は AGIC と同様に federated 前提
  - `resourceToggles.kedaController=true` かつ `resourceToggles.federatedCredential=true`

### AGIC の namespace 方針

- AGIC 用 namespace は backend と同一である必要はない。
- 推奨は `ingress` の専用 namespace に分離すること。
  - 理由:
    - コントローラと業務アプリの責務分離が明確になる
    - RBAC / Workload Identity / 運用権限を分離しやすい
    - 障害時の切り分けと運用作業が容易になる
