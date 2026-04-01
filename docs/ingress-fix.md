# Ingress Fix Plan

## 背景

現状の AKS は Azure CNI Overlay を採用している。

- `infra/common.parameter.json`
  - `aks.podCidr: "10.189.0.0/17"`
  - `aks.serviceCidr: "10.47.0.0/24"`
- `infra/lib/post-actions.sh` で生成される `scripts/init/agicController/deploy.sh` は、AGIC Helm chart (`ingress-azure`) を使って App Gateway と AKS Ingress を連携する
- AGIC は Kubernetes Ingress の backend Service を解決した結果として、App Gateway backend pool に Endpoint IP を登録する
- Azure CNI Overlay では、その Endpoint IP は Pod IP になる

今回確認できた事実:

- Service
  - `r-3pull-test-api -> 10.47.0.72:8000`
  - `r-3pull-test-web -> 10.47.0.198:3000`
- Endpoint / Pod
  - `r-3pull-test-api -> 10.189.4.241:8000`
  - `r-3pull-test-web -> 10.189.2.190:3000`
- AGIC は Ingress を App Gateway に反映できている
  - `Applied generated Application Gateway configuration`
- しかし App Gateway health probe は Pod IP 宛で timeout している

参考: Microsoft Learn の AGIC 概要では、AGIC は Azure CNI Overlay をサポートするが、前提条件として以下が必要。

- AGIC `v1.9.1+`
- Application Gateway subnet は `maximum /24 prefix`
- Application Gateway subnet に `Microsoft.Network/applicationGateways` の delegation

https://learn.microsoft.com/en-us/azure/application-gateway/ingress-controller-overview

## 現状のコード上の確認

### 1. App Gateway subnet サイズ

現在の subnet 定義:

- `infra/config/subnets.json`
  - `ApplicationGatewaySubnet`: `/25`
  - `ApplicationGatewayLowLatencySubnet`: `/25`

現在の VNet address space:

- `infra/common.parameter.json`
  - `10.189.128.0/24`
  - `10.189.129.0/24`
  - `10.189.130.0/24`
  - `10.189.131.0/24`

つまり全体では `/22` 相当、1024 アドレス分。

現在の subnet 消費量:

- Bastion `/26` = 64
- Firewall `/26` = 64
- Maintenance `/29` = 8
- PrivateEndpoint `/26` = 64
- AppGateway `/25` = 128
- AppGatewayLowLatency `/25` = 128
- AgentNode `/26` = 64
- UserNode `/24` = 256

合計 776 アドレス相当。

Microsoft Learn の `maximum /24 prefix` は、「/24 より大きい subnet を使ってはいけない」という意味であり、`/25` や `/26` は要件を満たす。

つまり:

- `/23` は不可
- `/24` は可
- `/25` は可
- `/26` は可

したがって、現在の `ApplicationGatewaySubnet` `/25`、`ApplicationGatewayLowLatencySubnet` `/25` は、**サイズ要件だけを見る限り問題ない**。

ここで App Gateway 2 subnet を `/24` に広げると:

- 現在 776
- `/25 -> /24` で standard 側 +128
- `/25 -> /24` で low latency 側 +128
- 合計 1032

結論:

- 現在の 4 x `/24` の VNet では、**他 subnet を維持したまま App Gateway 2 subnet を両方 `/24` にするのは収まらない**
- ただし、これは「将来 `/24` に広げたい場合」の容量試算であって、**現時点の `/25` が要件違反という意味ではない**
- standard 側だけ `/24` に広げるなら 904 で収まる
- low latency 側も `/24` に広げるなら、VNet address space を増やすか、他 subnet 設計を見直す必要がある

## 2. Subnet delegation

現状の subnet 作成:

- `infra/bicep/main.subnets.bicep`

`properties` に `delegations` が無い。

つまり、

- `ApplicationGatewaySubnet`
- `ApplicationGatewayLowLatencySubnet`

のどちらにも `Microsoft.Network/applicationGateways` delegation が IaC で付与されていない。

これは Azure CNI Overlay + AGIC の前提を満たしていない。

## 3. AGIC バージョン

現状の AGIC 導入元:

- `infra/lib/post-actions.sh`
- 生成物: `scripts/init/agicController/deploy.sh`

Helm chart:

- `oci://mcr.microsoft.com/azure-application-gateway/charts/ingress-azure`

実際の AGIC Pod イメージ:

- `mcr.microsoft.com/azure-application-gateway/kubernetes-ingress:1.9.8`

結論:

- 現在の AGIC は `1.9.8`
- Overlay 対応条件の `v1.9.1+` は満たしている
- したがって、まず疑うべきは AGIC バージョンではなく subnet 条件

## 修正方針

### 方針 1. App Gateway subnet サイズは現状維持でよい

整理:

- `maximum /24 prefix` のため、`/25` は許容範囲
- 現状の `ApplicationGatewaySubnet` `/25`、`ApplicationGatewayLowLatencySubnet` `/25` は、サイズ要件上は問題ない

結論:

- App Gateway subnet の `/24` 化は **必須ではない**
- したがって今回の修正対象としての優先度は低い
- ただし将来 `/24` に拡張したくなった場合は、現行 VNet address space では 2 本とも `/24` にする余裕がない

### 方針 2. Application Gateway subnet に delegation を付ける

対象:

- `ApplicationGatewaySubnet`
- `ApplicationGatewayLowLatencySubnet`

追加内容:

- `Microsoft.Network/applicationGateways` delegation

実装箇所:

- `infra/bicep/main.subnets.bicep`
- 必要に応じて `infra/config/subnets.json` に delegation 情報を持たせる

### 方針 3. AGIC バージョンは現状維持でよい

現状:

- AGIC `1.9.8`

結論:

- Overlay 対応条件は満たしているため、AGIC バージョンを優先的に上げる必要は低い
- まずは subnet 条件を満たした上で再検証する

## 実施順

1. `main.subnets.bicep` に delegation を追加する
2. `infra/main.sh` を再実行して subnet / AppGW / AGIC 関連を再適用する
3. AGIC 再導入または再同期後、以下を確認する
   - `kubectl logs -n ingress deploy/agic-standard-ingress-azure`
   - `kubectl logs -n ingress deploy/agic-lowlatency-ingress-azure`
   - App Gateway backend health
   - `kubectl get ingress -n application`

## 今回の判断

今回の情報からは、主因候補は次に絞られる。

- Application Gateway subnet delegation が IaC に入っていない
- その結果、Azure CNI Overlay + AGIC の前提条件を満たせていない可能性
App Gateway subnet の `/25` 自体は、Microsoft Learn の `maximum /24 prefix` 条件に照らすと問題ない。

AGIC バージョンは現状 `1.9.8` であり、優先度は低い。
