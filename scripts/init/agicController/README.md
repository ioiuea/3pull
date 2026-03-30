# AGIC Init Script

このディレクトリの `deploy.sh` は `infra/main.sh` 実行時に自動生成されます。

## AGIC とは

AGIC（Application Gateway Ingress Controller）は、AKS 上の Ingress 定義を Azure Application Gateway の設定に同期するコントローラです。  
Kubernetes 側で Ingress を更新すると、AGIC が Application Gateway のルーティング設定やバックエンドプールを反映します。

## なぜ導入するのか

- AKS への外部アクセス経路（L7 ルーティング、TLS 終端、WAF 連携）を Azure Application Gateway に統一するため
- Ingress 定義を通じて、アプリ側の公開設定を Kubernetes の宣言的な管理に寄せるため
- 手動で Application Gateway の設定を変更する運用を減らし、設定ミスや更新漏れを防ぐため

- 生成元: `infra/main.sh`
- 目的: メンテナンス VM などから AGIC（standard / low-latency）を Helm で導入・更新する
- 内容: 実行環境の固有情報（AKS 名、Application Gateway ID、Managed Identity clientId など）を埋め込んだコマンド

注意:

- `deploy.sh` は `infra/main.sh` 再実行時に上書きされます。
- 手動編集は推奨しません。変更が必要な場合は `infra/main.sh` 側を修正してください。
- AGIC は chart 実装上の ServiceAccount 名として `agic-standard-sa-ingress-azure` / `agic-lowlatency-sa-ingress-azure` を使う前提です。federated credential 側も同じ subject に揃える必要があります。
- `kubectl logs -n ingress deploy/agic-standard-ingress-azure` などで `AADSTS700213` が出る場合は、Managed Identity 側 federated credential の subject と実際の ServiceAccount 名が不一致です。
