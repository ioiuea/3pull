# services

`app.services` は、アプリケーションのユースケースを実装するパッケージです。

この層の責務は、認証、監査ログ記録、非同期ジョブ投入などの業務処理をまとめ、必要に応じて複数の repository や adapter を組み合わせて実行することです。

## この層に置くもの

- ユースケース単位の処理
- 複数 repository / adapter を束ねる業務フロー
- 認証、監査、ジョブ投入などアプリケーション固有の処理手順
- transaction 境界の中で行う更新処理の組み立て

## この層に置かないもの

- HTTP endpoint 定義
- SQLAlchemy model 定義
- 単純な DB CRUD
- Azure / Redis などの接続実装

`services` は「何を実現するか」を担当し、「HTTP でどう受けるか」は `api`、「DB にどう保存するか」は `repositories`、「外部にどう接続するか」は `adapters` に分離します。

## 構成

- `auth/`
  - アカウント作成、メール認証、ログイン、パスワード変更、セッション管理
- `audit/`
  - 認証監査ログの記録
- `jobs/`
  - 非同期ジョブ row 作成と queue dispatch

## 利用方針

service は router、worker、scheduler などから呼び出します。

```python
from app.services.auth.auth_account_service import authenticate_email_user
from app.services.jobs.async_job_dispatcher import dispatch_async_job
```

service の中では必要に応じて repository や adapter を呼びますが、逆方向の依存は持たせないようにします。

## 関連 package

- `app.api`
  - service を HTTP endpoint から呼び出す入口
- `app.repositories`
  - DB 永続化 access
- `app.adapters`
  - 外部サービス接続
- `app.workers`
  - service が投入した非同期ジョブを実行する層
