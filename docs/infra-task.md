# Infra タスク整理

## Ingress 要件（確定）

### 1. コントローラ方式

- AGIC addon を継続利用する（AKS の `ingressApplicationGateway` addon 前提）。

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
