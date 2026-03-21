# models

`app.models` は、DB テーブルに対応する SQLAlchemy ORM model をまとめるパッケージです。

この層の責務は、テーブル構造、カラム定義、Enum、リレーションなど、永続化モデルをコードとして表現することです。

## この層に置くもの

- SQLAlchemy ORM model
- テーブル名、schema 名、カラム定義
- ORM 上の Enum や relationship
- 永続化モデルとして必要な最小限の補助定義

## この層に置かないもの

- API response schema
- 業務ロジック
- DB query / CRUD の実装
- HTTP request / response の制御

`models` は DB 上の表現であり、API 契約やユースケースそのものを表す層ではありません。

## 構成

- `auth/`
  - `auth` schema に対応する ORM model 群
  - ユーザー、認証 ID、セッション、メール検証 token、パスワードリセット token
- `audit/`
  - `audit` schema に対応する ORM model 群
  - 認証監査ログ
- `jobs/`
  - `core` schema 内のうち、非同期ジョブで利用するテーブルをまとめた ORM model 群
  - 現状は `core` schema 全体を `models/core/` のように持たず、非同期ジョブ関連だけを `jobs/` として切り出して管理している

`auth` と `audit` は DB schema と 1:1 で対応するフォルダです。  
一方で `core` schema は今後通常の core テーブル群も管理対象になる想定ですが、現時点では非同期ジョブ関連テーブルだけを例外的に `jobs/` フォルダで管理しています。

## 利用方針

ORM model は主に repository や service から利用します。

```python
from app.models.auth.user import User
from app.models.jobs.async_job import AsyncJob
```

一方で、API response にそのまま返す用途には使いません。外部公開する形は `app.api.schemas` に定義し、router や service で必要な shape へ変換します。

## 関連 package

- `app.repositories`
  - ORM model を使った query / CRUD
- `app.api.schemas`
  - HTTP request / response schema
- `app.services`
  - model と repository を組み合わせる業務ロジック
