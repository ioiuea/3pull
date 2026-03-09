# KEDA Init Script

このディレクトリの `deploy.sh` は `infra/main.sh` 実行時に自動生成されます。

## KEDA とは

KEDA（Kubernetes Event-driven Autoscaling）は、イベントや外部メトリクスをもとに Kubernetes の Pod 数を自動調整する仕組みです。  
通常の CPU/メモリ指標だけでなく、キュー長などのワークロード量に応じたスケーリングができます。

## なぜ導入するのか

- バッチ処理や非同期処理を、実際の負荷（メッセージ量など）に合わせて自動で増減させるため
- アイドル時は Pod 数を減らしてコストを抑え、ピーク時は迅速にスケールして処理遅延を抑えるため
- 手動スケール運用を減らし、負荷変動への追従を安定させるため

- 生成元: `infra/main.sh`
- 目的: メンテナンス VM などから KEDA を Helm で導入・更新する
- 内容: 実行環境の固有情報（AKS 名、Managed Identity clientId、namespace / ServiceAccount 名 など）を埋め込んだコマンド

注意:

- `deploy.sh` は `infra/main.sh` 再実行時に上書きされます。
- 手動編集は推奨しません。変更が必要な場合は `infra/main.sh` 側を修正してください。
