# repositories

`app.repositories` は、DB への永続化 access をまとめるパッケージです。

この層の責務は、SQLAlchemy `Session` と ORM model を使って query / insert / update / delete を行うことです。

## この層に置くもの

- ORM model に対する CRUD
- 一覧取得、検索、条件付き取得
- DB 永続化のための update / delete 処理
- transaction 内で使う永続化 helper

## この層に置かないもの

- HTTP request / response の制御
- 認証やジョブ処理の業務ロジック
- 外部サービス連携
- アプリ設定や middleware

repository は「DB にどうアクセスするか」を担当し、「なぜその操作をするか」の業務判断は service 層に残します。

## 構成

- `auth/`
  - `auth` schema に対応する repository 群
  - `auth` schema 系 model の query / CRUD
- `audit/`
  - `audit` schema に対応する repository 群
  - `audit` schema 系 model の query / insert
- `jobs/`
  - `core` schema 内のうち、非同期ジョブ関連 table を扱う repository 群
  - 非同期ジョブ関連 table の query / CRUD

`auth` と `audit` は DB schema と 1:1 で対応するフォルダです。  
一方で `core` schema は今後通常の core テーブル群も管理対象になる想定ですが、現時点では非同期ジョブ関連テーブルだけを例外的に `jobs/` フォルダで管理しています。

## 利用方針

repository は通常、service や worker から SQLAlchemy `Session` とともに呼び出します。

```python
from sqlalchemy.orm import Session

from app.repositories.auth.user_repository import find_user_by_email


def load_user(session: Session, email: str):
    return find_user_by_email(session, email)
```

repository 自体は FastAPI や router へ依存しないようにします。

## 関連 package

- `app.models`
  - repository が永続化対象として扱う ORM model
- `app.services`
  - 複数 repository を束ねる業務ロジック
- `app.adapters.sql`
  - DB 接続と SQLAlchemy session 生成
