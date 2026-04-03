# ApplicationGatewaySubnet /24 化 変更整理

## 目的

このドキュメントは、`ApplicationGatewaySubnet` のサブネットプレフィクスを `/24` へ見直す作業にフォーカスして、影響範囲、想定作業、変更予定ファイルを整理するためのメモです。

既に対応済みの事項や、今回の変更対象ではない調査論点は含めません。

## 変更対象

今回の主対象は以下です。

- `ApplicationGatewaySubnet` を `/24` 化する

今回の主対象外:

- AGIC の導入方式変更
- AGIC バージョン更新
- Ingress manifest のルーティング仕様変更
- backend / frontend アプリ実装変更

## 現状

### サブネット定義

現状の固定定義は以下です。

- `infra/config/subnets.json`
  - `ApplicationGatewaySubnet`: `prefixLength = 24`
  - `ApplicationGatewayLowLatencySubnet`: `prefixLength = 24`

### VNet address space

現状の VNet address space は以下です。

- `infra/common.parameter.json`
  - `10.189.128.0/24`
  - `10.189.129.0/24`
  - `10.189.130.0/24`
  - `10.189.131.0/24`

### 低遅延用 App Gateway サブネット

現状の `infra/common.parameter.json` では以下です。

- `network.enableLowLatencyApplicationGatewaySubnet = false`

したがって、現時点で実際に利用される App Gateway 系サブネットは通常系の `ApplicationGatewaySubnet` が中心です。ただし、固定定義やドキュメントには low-latency 用の定義も存在するため、変更方針次第では合わせて見直しが必要です。

## 変更の前提

このリポジトリでは、サブネット CIDR は固定で直書きされているのではなく、以下の流れで再計算されます。

- `infra/config/subnets.json`
  - 各サブネットの `prefixLength` を定義
- `infra/common.parameter.json`
  - `network.vnetAddressPrefixes` を定義
- `infra/scripts/generate-subnets-params.py`
  - 上記 2 つをもとに、各サブネットの `addressPrefix` を順番に自動割り当て
- `infra/bicep/main.subnets.bicep`
  - 生成された subnet 一覧を受けて Azure に反映

そのため、`ApplicationGatewaySubnet` の `/24` 化は単純な 1 ファイル変更ではなく、VNet 全体の収まり方を含めて確認が必要です。

## 影響範囲

### 1. サブネット割当て順序と CIDR の変化

`infra/scripts/generate-subnets-params.py` は、`prefixLength` 昇順でサブネットを割り当てます。

そのため、`ApplicationGatewaySubnet` を `/24` にすると、以下に影響します。

- `ApplicationGatewaySubnet` 自身の CIDR
- それ以降に割り当てられる他サブネットの CIDR
- `ApplicationGatewayLowLatencySubnet` を有効化した場合の全体収まり

特に、既存の `/25` 前提で記載されている経路図、説明、運用メモは更新対象になります。

### 2. VNet address space の容量確認

現状の VNet は `/24` を 4 本持つ構成です。

`ApplicationGatewaySubnet` のみを `/24` に広げる場合でも、他サブネットとの配置順や競合状況を再確認する必要があります。

確認ポイント:

- 通常系のみ `/24` にして既存 address space に収まるか
- 将来的に `ApplicationGatewayLowLatencySubnet` も `/24` にする余地を残すか
- `UserNodeSubnet` `/24` を維持したまま成立するか
- 既存環境に対して再デプロイ時の CIDR 変更影響を許容できるか

### 3. App Gateway / Route Table / NSG 関連ドキュメント

App Gateway subnet の CIDR はコードだけでなく、複数ドキュメントに埋め込まれています。

影響対象:

- 構成図
- UDR 説明
- NSG 説明
- App Gateway 関連の前提説明

### 4. パラメータ生成スクリプトの動作確認

以下のスクリプトはサブネット定義を参照して動くため、`/24` 化後の再確認が必要です。

- `infra/scripts/generate-subnets-params.py`
- `infra/scripts/generate-application-gateway-params.py`
- `infra/scripts/generate-application-gateway-low-latency-params.py`
- `infra/scripts/generate-subnet-attachments-params.py`
- `infra/scripts/sync-backend-values.py`

これらのスクリプト自体を変更しない場合でも、出力結果が変わる可能性があります。

## 想定作業

### 作業 1. `ApplicationGatewaySubnet` の prefixLength を `/24` に変更

対象:

- `infra/config/subnets.json`

想定変更:

- `ApplicationGatewaySubnet.prefixLength`
  - `24` を維持する

補足:

- `ApplicationGatewayLowLatencySubnet` を今回どう扱うかは別途判断が必要
- 今回の主眼が通常系のみなら、low-latency 側は現状維持も選択肢

### 作業 2. 必要なら VNet address space を見直す

対象候補:

- `infra/common.parameter.json`

想定変更:

- `network.vnetAddressPrefixes` の再設計

判断が必要な点:

- 現行の 4 x `/24` で十分か
- low-latency 用 subnet の将来拡張を見込むか
- 環境再作成なしで吸収できるか

### 作業 3. 生成結果の再確認

対象:

- `infra/scripts/generate-subnets-params.py` の生成結果
- `infra/params/*` の生成物

確認内容:

- `ApplicationGatewaySubnet` の CIDR が想定通り `/24` になっていること
- 他サブネットが意図しない CIDR にずれていないこと
- `enableLowLatencyApplicationGatewaySubnet=false` の現行条件で破綻しないこと

### 作業 4. 関連ドキュメントの更新

対象:

- `infra/README.md`
- `docs/infra/network.md`
- `docs/infra/agw.md`

想定変更:

- `ApplicationGatewaySubnet` のサイズ表記
- 構成図内の CIDR 表記
- 必要アドレス空間の説明
- 低遅延オプション時の容量説明

### 作業 5. 既存環境への適用手順整理

今回の変更は subnet prefix の変更を伴うため、既存 Azure 環境に対しては注意が必要です。

整理対象:

- 既存 subnet のインプレース変更可否
- 既存 App Gateway が配置済みの場合の再作成要否
- subnet 再作成時の依存リソース影響
- 環境再構築が必要かどうか

この観点は実装前に明示しておく必要があります。

## 変更予定ファイル

### 直接変更候補

- `infra/config/subnets.json`
- `infra/common.parameter.json`
- `infra/README.md`
- `docs/infra/network.md`
- `docs/infra/agw.md`
- `docs/ingress-fix.md`

### 影響確認対象

- `infra/scripts/generate-subnets-params.py`
- `infra/scripts/generate-application-gateway-params.py`
- `infra/scripts/generate-application-gateway-low-latency-params.py`
- `infra/scripts/generate-subnet-attachments-params.py`
- `infra/scripts/sync-backend-values.py`
- `infra/bicep/main.subnets.bicep`

## 実装前に決めるべきこと

### 1. low-latency 用サブネットも今回合わせて `/24` にするか

選択肢:

- 通常系 `ApplicationGatewaySubnet` のみ `/24`
- 通常系 / 低遅延系の両方を `/24`

この判断で、必要な VNet address space と関連ドキュメントの更新範囲が変わります。

### 2. 既存環境へ適用するのか、新規構築前提にするのか

subnet prefix 変更は既存環境への差分適用が難しい可能性があります。

整理が必要な観点:

- 既存リソース温存を優先するか
- 一時的な停止を許容するか
- 検証環境で先に subnet 再設計を試すか

### 3. VNet 全体を拡張するか

将来的に low-latency 側も `/24` に揃える想定があるなら、今回の時点で `vnetAddressPrefixes` も広げる方が再設計回数は減ります。

## このドキュメントの位置づけ

このドキュメントは、`ApplicationGatewaySubnet` の `/24` 化に向けた変更整理メモです。

実際の実装に着手する際は、以下を別途作る想定です。

- 実装方針確定版
- 実施手順
- 変更後の検証項目
