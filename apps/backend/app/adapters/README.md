# adapters

`app.adapters` は、外部サービスや外部システムとの接続処理をまとめるパッケージです。

この層の責務は、Azure SQL、Redis、Azure Service Bus、Azure Blob Storage、Microsoft Entra ID など、アプリケーション外部との境界を実装することです。

## この層に置くもの

- 外部サービス client の生成
- 接続設定の解決
- API / SDK 呼び出し
- トークン注入や接続確立などのインフラ寄り処理

## この層に置かないもの

- HTTP endpoint 定義
- 業務ロジックやユースケース
- DB 永続化の query / CRUD
- Pydantic request / response schema

外部接続そのものは `adapters` に置き、その接続をどう使って業務を実現するかは `services` や `workers` 側で扱います。

## 構成

- `sql/`
  - Azure SQL 接続、engine / session 生成、access token 注入
- `cache/`
  - Redis client 生成
- `queue/`
  - Azure Service Bus client とメッセージ送信
- `storage/`
  - Azure Blob Storage 入出力
- `idp/`
  - Microsoft Entra ID 連携
- `network/`
  - TCP 到達性確認などの低レベル疎通処理

## 利用方針

adapter は外部境界の薄いラッパーとして保ちます。業務ルールや分岐が増える場合は service 層へ寄せます。

```python
from app.adapters.storage.azure_blob import upload_bytes
from app.adapters.queue.message_sender import send_message
```

また、adapter は `core.settings` や SDK client に依存して構いませんが、router に直接依存しないようにします。

## 関連 package

- `app.core.settings`
  - 接続設定の解決
- `app.services`
  - adapter を組み合わせるユースケース
- `app.repositories`
  - DB 内の永続化 access
- `app.workers`
  - queue / storage adapter を使う非同期実行本体
