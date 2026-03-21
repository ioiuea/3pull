# Backend

`apps/backend` は FastAPI + SQLAlchemy + Alembic を使った backend 実装です。  
認証、監査ログ、非同期ジョブ、cleanup scheduler を 1 つのアプリケーションとして管理します。

## 技術スタック

- API: FastAPI
- ORM / Migration: SQLAlchemy, Alembic
- DB: Azure SQL Database
- Auth: Microsoft Entra ID, Email/Password
- Queue: Azure Service Bus
- Storage: Azure Blob Storage
- Package manager: `uv`
- Lint / Typecheck / Test: `ruff`, `pyright`, `pytest`

## 開発コマンド

- 依存同期: `make backend-install`
- format check: `make backend-format`
- lint: `make backend-lint`
- typecheck: `make backend-typecheck`
- test: `make backend-test`
- migration 生成: `make alembic-revision "message"`
- migration 適用: `make alembic-upgrade`
- API 起動: `make dev-api`
- worker 起動: `make dev-worker`
- worker 個別起動:
  - `make dev-worker-auth-audit-export`
  - `make dev-worker-sample-wait-blob`
- cleanup dry-run:
  - `make schedulers-sessions-dry-run`
  - `make schedulers-audit-dry-run`
  - `make schedulers-jobs-dry-run`

## 初期セットアップ

1. `apps/backend/.env` を用意する  
   `make env`
2. `az login` を済ませる
3. Azure SQL の schema / Entra user / schema 権限を投入する  
   `./scripts/init/sql/deploy.sh -local`
4. Alembic を適用する  
   `make alembic-upgrade`
5. API を起動する  
   `make dev-api`

補足:

- `deploy.sh` は `auth` / `audit` / `core` schema を作成し、現在の `az login` ユーザーを Azure SQL の external user として登録し、各 schema への権限を付与します。
- schema 作成は Alembic ではなく `deploy.sh` の責務です。

## フォルダ構成

```text
apps/backend
├── .env.example                           # backend 用の環境変数サンプル
├── alembic.ini                            # Alembic 実行設定
├── pyproject.toml                         # backend 依存関係と各種ツール設定
├── alembic/                               # DB マイグレーション管理
│   ├── env.py                             # Alembic 実行コンテキスト
│   └── versions/                          # 生成済み migration 履歴
│       └── 6177c957a67e_init_table_schemas.py
└── app/                                   # アプリケーション本体
    ├── main.py                            # FastAPI アプリ生成と router 登録
    ├── api/                               # HTTP インターフェース層
    │   ├── internal/                      # `/livez` `/readyz` など内部運用向け API
    │   │   └── probes.py
    │   ├── routers/                       # エンドポイント定義
    │   │   ├── audit.py                   # 監査ログ API
    │   │   ├── auth.py                    # 認証 API
    │   │   ├── health.py                  # health API
    │   │   └── jobs/                      # 非同期ジョブ API を機能別に分割
    │   │       ├── __init__.py
    │   │       ├── commands.py            # cancel など更新系
    │   │       ├── helpers.py             # 共通認可/変換ヘルパー
    │   │       ├── query.py               # 一覧/詳細/成果物参照
    │   │       └── create/                # job_type ごとの作成 API
    │   └── schemas/                       # Request / Response の Pydantic 定義
    │       ├── audit.py
    │       ├── auth.py
    │       ├── health.py
    │       └── jobs.py
    ├── adapters/                          # 外部サービス接続の抽象化層
    │   ├── cache/                         # Redis client 生成
    │   ├── idp/                           # IdP 連携
    │   ├── network/                       # TCP 到達性確認などの疎通処理
    │   ├── queue/                         # Azure Service Bus 送受信
    │   ├── sql/                           # Azure SQL 接続と access token 注入
    │   └── storage/                       # Azure Blob Storage 入出力
    ├── core/                              # 横断基盤層
    │   ├── lifecycle/                     # startup / shutdown 処理
    │   ├── logging/                       # structlog とアクセスログ設定
    │   ├── security/                      # password / CSRF / API protect / token 暗号化
    │   │   ├── client_ip.py               # trusted proxy 前提の client IP 解決
    │   │   ├── csrf.py                    # Origin/Referer ベース CSRF 保護
    │   │   ├── password.py                # password hash / verify
    │   │   ├── rate_limit/                # Redis ベース IP rate limit
    │   │   │   ├── models.py              # policy / decision などの型
    │   │   │   ├── store.py               # Redis 操作
    │   │   │   ├── service.py             # rate limit 判定
    │   │   │   └── fastapi.py             # FastAPI guard
    │   │   ├── session.py                 # session cookie ベース API protect
    │   │   └── token_cipher.py            # token 暗号化/復号
    │   ├── settings/                      # AppSettings と環境変数解決
    │   └── datetime.py                    # UTC 正規化など共通 utility
    ├── models/                            # SQLAlchemy ORM テーブル定義
    │   ├── audit/                         # 監査ログ系テーブル
    │   ├── auth/                          # 認証・セッション系テーブル
    │   └── jobs/                          # 非同期ジョブ基盤テーブル
    ├── repositories/                      # DB 永続化アクセス層
    │   ├── audit/                         # audit schema 向け query / CRUD
    │   ├── auth/                          # auth schema 向け query / CRUD
    │   └── jobs/                          # core schema 内非同期ジョブ向け query / CRUD
    ├── schedulers/                        # 定期 cleanup CLI と実行単位
    │   ├── scheduler_cleanup.py           # cleanup CLI エントリーポイント
    │   └── cleanup/                       # 対象別 cleanup ロジック
    │       ├── helpers.py
    │       ├── runner_registry.py         # subcommand と runner の対応付け
    │       └── runners/
    ├── services/                          # ユースケース層
    │   ├── audit/                         # 監査ログ記録ユースケース
    │   ├── auth/                          # 認証フロー
    │   └── jobs/                          # job row 作成と queue dispatch
    └── workers/                           # Service Bus worker 実装
        ├── runtime.py                     # 共通 worker 実行ループ
        ├── job_registry.py                # job_type と実行関数の対応表
        ├── entrypoints/                   # worker 起動モジュール
        ├── jobs/                          # 実ジョブ処理本体
        └── messages/                      # Queue メッセージ定義
```

### レイヤ責務

- `api/`: HTTP 入出力、FastAPI router、Pydantic schema
- `services/`: ユースケース、複数 repository を束ねる業務ロジック
- `repositories/`: SQLAlchemy Session を使った CRUD / query
- `models/`: SQLAlchemy ORM テーブル定義
- `adapters/`: Redis / Azure SQL / Service Bus / Blob / Entra などの外部接続
- `workers/`: 非同期ジョブの実行本体
- `schedulers/`: cleanup 系 CLI
- `core/`: 設定、ログ、セキュリティ、共通 utility

## API 構成

公開 API は `/backend` 配下に集約しています。

- `GET /backend/health`
- `GET /backend/auth/me`
- `POST /backend/auth/email/signup`
- `POST /backend/auth/email/verify`
- `POST /backend/auth/email/login`
- `POST /backend/auth/password/reset/request`
- `POST /backend/auth/password/reset/confirm`
- `POST /backend/auth/password/change`
- `GET /backend/auth/entra/login`
- `GET /backend/auth/entra/callback`
- `GET /backend/auth/entra/profile`
- `POST /backend/auth/logout`
- `POST /backend/auth/session/refresh`
- `GET /backend/audit/audit-logs`
- `GET /backend/jobs`
- `GET /backend/jobs/{job_id}`
- `POST /backend/jobs/{job_id}/cancel`
- `GET /backend/jobs/{job_id}/artifacts/{artifact_id}/download`
- `POST /backend/jobs/auth-audit-export`
- `POST /backend/jobs/sample-wait-blob`

内部プローブは `/backend` の外に公開します。

- `GET /livez`
- `GET /readyz`

## 認証方針

認証方式は 2 系統です。

- Entra ID: internal ユーザー向け
- Email/Password: external ユーザー向け

主要仕様:

- セッションは DB の `auth.sessions` で管理
- Cookie は `HttpOnly` を利用
- CSRF は `Origin/Referer` 検証ミドルウェアで保護
- 認証系 API には IP ベース rate limit を適用
- パスワードは Argon2id でハッシュ化
- Email verification token / password reset token は SHA-256 ハッシュのみ保存
- Entra の access token / refresh token は暗号化して保存
- `/backend/auth/entra/profile` は internal ユーザーのみ許可

### API Security

設計原則:

1. セキュリティポリシーは `app/core/security` に置く。
2. 認証ドメイン本体は `app/services/auth` に置く。
3. router は HTTP 入出力と `Depends(...)` / guard 呼び出しの接着に限定する。
4. `app/api/dependencies` は使わない。
5. 同じ保護手段を複数 router で使う場合、router helper に重複実装しない。

レイヤ責務:

- `app/core/security`
  - API 保護の共通ルール
  - FastAPI から使う guard
  - client IP 解決
  - session cookie ベース API protect
  - rate limit policy 適用
- `app/services/auth`
  - 認証/セッションのドメイン処理
  - DB を使った user/session 解決
  - 認証失敗をドメインエラーとして返す
- `app/api/routers`
  - route 定義
  - request/response schema の接着
  - `Depends(...)` の適用
  - guard 通過後の業務処理

実装構成:

```text
apps/backend/app/
  core/
    security/
      client_ip.py
      csrf.py
      rate_limit/
        __init__.py
        models.py
        store.py
        service.py
        fastapi.py
      session.py
  services/
    auth/
      session_auth_service.py
  api/
    routers/
      auth.py
      health.py
      audit.py
      jobs/
        helpers.py
        query.py
        commands.py
        create/
```

#### Rate Limit

対象実装:

- `app/core/security/rate_limit/models.py`
- `app/core/security/rate_limit/store.py`
- `app/core/security/rate_limit/service.py`
- `app/core/security/rate_limit/fastapi.py`
- `app/api/routers/auth.py`

モジュール責務:

- `models.py`
  - `RateLimitPolicyKey`、`RateLimitPolicy`、`RateLimitDecision` などの型を持つ。
- `store.py`
  - Redis への読み書きだけを担当する。
  - request counter / failure counter / block key の更新と TTL 管理を行う。
- `service.py`
  - settings から policy を構築する。
  - request/failure を評価し、`RateLimitDecision` を返す。
- `fastapi.py`
  - `Request` から client IP を解決する。
  - `RateLimitService` を呼ぶ。
  - fail-open / observe / enforce を HTTP 応答へ反映する。

router からの利用:

```python
from app.core.security.rate_limit.fastapi import require_rate_limit

@router.post("/email/login")
async def post_email_login(
    ...,
    _: None = Depends(require_rate_limit(RateLimitPolicyKey.EMAIL_LOGIN)),
):
    ...
```

処理フロー:

```mermaid
flowchart TD
    A[Client Request] --> B[api/routers/auth.py]
    B --> C[Depends(require_rate_limit(policy_key))]
    C --> D[core/security/rate_limit/fastapi.py]
    D --> E[resolve_client_ips]
    D --> F[RateLimitService.evaluate_request]
    F --> G[RateLimitRedisStore]
    G --> H[(Redis)]
    F --> I{blocked?}
    I -- no --> J[router 本体を続行]
    I -- observe --> J
    I -- enforce --> K[HTTP 429]
```

処理順:

1. router が `Depends(require_rate_limit(policy_key))` を定義する。
2. `fastapi.py` が `Request` から `client IP` を解決する。
3. `RateLimitService.evaluate_request(...)` が block key を確認する。
4. block 中でなければ `store.py` が request counter を更新する。
5. 閾値超過時は block key を設定し、`RateLimitDecision(blocked=True)` を返す。
6. `observe` mode ではログのみ記録して request は通す。
7. `enforce` mode では `HTTP 429` を返す。
8. request 評価で block されなければ router 本体の処理へ進む。

failure counter の扱い:

```mermaid
flowchart TD
    A[router 本体で認証/検証失敗] --> B[_record_rate_limit_failure]
    B --> C[RateLimitService.record_failure]
    C --> D[RateLimitRedisStore]
    D --> E[(Redis)]
    C --> F{閾値超過?}
    F -- no --> G[通常の失敗応答]
    F -- yes --> H[block key を設定]
```

補足:

- failure counter の更新は router 本体から明示的に呼ぶ。
- どの API が failure counter を持つかは policy に依存する。
- `app/api/dependencies` は削除済みであり、rate limit dependency は `core/security` に置く。
- `store.py` は役割としては repository 相当だが、security モジュール専用の Redis store として `core/security` 内に置く。

#### Session Protect

対象実装:

- `app/core/security/session.py`
- `app/services/auth/session_auth_service.py`
- `app/api/routers/auth.py`
- `app/api/routers/health.py`
- `app/api/routers/audit.py`
- `app/api/routers/jobs/*`

モジュール責務:

- `session.py`
  - cookie 名の解決
  - raw session token の取得
  - `SessionAuthError -> HTTP 401` 変換
  - `require_session_context`
  - `require_session_user`
  - `require_authenticated_session`
- `session_auth_service.py`
  - session 発行
  - session ローテーション
  - session 失効
  - raw token から有効 session / user を解決

guard 一覧:

- `require_session_context(request, session) -> AuthenticatedSessionContext`
  - user と raw token の両方が必要な endpoint 用
- `require_session_user(request, session) -> User`
  - user だけ取れればよい endpoint 用
- `require_authenticated_session(request, session) -> None`
  - 認証済み確認だけでよい endpoint 用

共通 guard を使う API:

- `GET /backend/auth/me`
- `GET /backend/auth/entra/profile`
- `POST /backend/auth/password/change`
- `GET /backend/health`
- `GET /backend/audit/audit-logs`
- `GET /backend/jobs`
- `GET /backend/jobs/{job_id}`
- `POST /backend/jobs/{job_id}/cancel`
- `GET /backend/jobs/{job_id}/artifacts/{artifact_id}/download`
- `POST /backend/jobs/auth-audit-export`
- `POST /backend/jobs/sample-wait-blob`

補足:

- `POST /backend/auth/logout`
- `POST /backend/auth/session/refresh`

は session cookie を使うが、未認証時の扱いが通常 guard と異なるため、
router 側で `resolve_session_cookie_token(...)` を直接使う。

処理フロー:

```mermaid
flowchart TD
    A[Client Request with Session Cookie] --> B[api/routers/*.py]
    B --> C[require_session_user / require_session_context]
    C --> D[core/security/session.py]
    D --> E[request.cookies から raw token を取得]
    D --> F[resolve_user_by_session_token]
    F --> G[services/auth/session_auth_service.py]
    G --> H[(auth.sessions / auth.users)]
    F --> I{valid session?}
    I -- no --> J[session.py が HTTP 401 に変換]
    I -- yes --> K[User または Context を router へ返す]
    K --> L[router 本体を続行]
```

処理順:

1. router が `require_session_user(...)` または `require_session_context(...)` を呼ぶ。
2. `session.py` が settings から cookie 名を解決し、raw token を取得する。
3. raw token を `session_auth_service.py` に渡して user を解決する。
4. service は DB 上の session / user を見て有効性を判定する。
5. 無効・期限切れ・user 不在なら `SessionAuthError` を返す。
6. `session.py` がそれを API 用の `401` に変換する。
7. 成功時は `User` または `AuthenticatedSessionContext` を router に返す。
8. router は取得した user/context を使って本体処理だけを続行する。

error 応答:

- session cookie 未設定
  - `HTTP 401`
  - `code: session_missing`
- session invalid / expired / user not found
  - `HTTP 401`
  - `code` は `SessionAuthError.code` をそのまま使う

logout / session refresh の特例:

- `logout`
  - cookie があれば失効を試みる
  - 無効 token でもログアウト成功として扱う
  - browser cookie は常に削除する
- `session/refresh`
  - cookie 未設定時は `session_missing` で `401`
  - 有効 token なら session をローテーションし、新 cookie を発行する

### Auth Rate Limit

認証系 API に適用する IP ベース rate limit の仕様は、上記 `Rate Limit` のうち
認証 API 向けの具体ポリシーを指します。

目的:

- ブルートフォース
- パスワードリセット乱発
- サインアップ乱発
- OIDC callback の過剰試行

を、`client IP + policy_key` 単位で制御する。

対象 API:

- `POST /backend/auth/email/signup`
- `POST /backend/auth/email/login`
- `POST /backend/auth/password/reset/request`
- `POST /backend/auth/password/reset/confirm`
- `GET /backend/auth/entra/login`
- `GET /backend/auth/entra/callback`

非対象:

- `/backend/auth/me`
- `/backend/auth/logout`
- `/backend/auth/session/refresh`
- jobs / audit / health などの認証以外 API

基本方針:

- 既存のアカウント単位ロックを置き換えず、補完する
- 判定単位は `client IP + policy_key`
- 共有ストアに `Azure Managed Redis` を使う
- 複数 Pod 構成でも同一判定になるようにする
- Redis 障害時は `fail-open`

クライアント IP 解決:

- `X-Forwarded-For` を常時信頼しない
- `TRUST_PROXY_HEADERS=true` かつ `TRUSTED_PROXY_CIDRS` に一致する trusted proxy 配下でのみ forward header を採用する
- それ以外は TCP peer address を `client IP` として扱う

補足:

- `TRUSTED_PROXY_CIDRS` は infra 側で Application Gateway サブネット CIDR から生成する

policy 一覧:

| API | policy_key |
| --- | --- |
| `POST /backend/auth/email/signup` | `email_signup` |
| `POST /backend/auth/email/login` | `email_login` |
| `POST /backend/auth/password/reset/request` | `password_reset_request` |
| `POST /backend/auth/password/reset/confirm` | `password_reset_confirm` |
| `GET /backend/auth/entra/login` | `entra_login` |
| `GET /backend/auth/entra/callback` | `entra_callback` |

判定ルール:

- request 時
  - block key を確認する
  - request counter を sliding window で評価する
  - 閾値超過時は block key を設定する
- response/失敗時
  - 必要な API では failure counter を更新する

Redis キー設計:

- namespace
  - `auth:ratelimit`
- request counter
  - `auth:ratelimit:counter:<policy_key>:req:<client_ip>`
- failure counter
  - `auth:ratelimit:counter:<policy_key>:fail:<client_ip>`
- block
  - `auth:ratelimit:block:<policy_key>:<client_ip>`

例:

- `auth:ratelimit:counter:email_login:req:203.0.113.10`
- `auth:ratelimit:counter:email_login:fail:203.0.113.10`
- `auth:ratelimit:block:email_login:203.0.113.10`

Redis データ構造:

- counter
  - Sorted Set
  - score は UNIX epoch milliseconds
- block
  - string key + TTL

TTL 方針:

- counter
  - policy の最長観測窓に合わせる
- block
  - policy ごとの block 秒数をそのまま TTL にする
- 手動解除
  - `block` key 削除で行う

運用方針:

- 標準の手動解除は block key のみ削除する
- counter key は通常削除しない
- ops script
  - [scripts/ops/ip-rate-limit/README.md](/Users/hiroki.ueda/Dev/3pull/scripts/ops/ip-rate-limit/README.md)
- maint-vm 運用時は `mi-[env]-[system]-redis-ops` を利用する

設定項目:

- `RATE_LIMIT_MODE`
- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_SSL`
- `TRUST_PROXY_HEADERS`
- `TRUSTED_PROXY_CIDRS`
- 各 `RATE_LIMIT_POLICY_*`

補足:

- `RATE_LIMIT_RESPONSE_MESSAGE` は環境変数化しない

検証で確認済みのこと:

- `email/login` で block されること
- `password/reset/request` で block されること
- `email/signup` で block されること
- block TTL 経過で解除されること
- 手動解除で即時解除できること
- Redis 障害時に fail-open で継続すること
- infra から `generated.env.sh` が生成されること

残タスク:

- AKS 上からの実接続確認
- 検証環境での複数 Pod 試験

## データベース設計

アプリケーションテーブルは 3 schema に分割しています。

- `auth`: 認証主体、認証トークン、セッション
- `audit`: 監査ログ
- `core`: 非同期ジョブ基盤

### テーブル一覧

- `auth.users`
- `auth.auth_identities`
- `auth.sessions`
- `auth.email_verification_tokens`
- `auth.password_reset_tokens`
- `audit.auth_audit_logs`
- `core.async_jobs`
- `core.async_job_artifacts`

### ER 図

```mermaid
erDiagram
    users {
        UUID id PK
        VARCHAR email
        VARCHAR email_normalized UK
        NVARCHAR display_name
        VARCHAR user_type
        BOOLEAN is_active
        DATETIME2 created_at
        DATETIME2 updated_at
    }

    auth_identities {
        UUID id PK
        UUID user_id FK
        VARCHAR provider
        VARCHAR provider_subject
        VARCHAR email_normalized
        VARCHAR password_hash
        INTEGER failed_login_count
        DATETIME2 locked_until
        DATETIME2 email_verified_at
        DATETIME2 last_login_at
        DATETIME2 created_at
        DATETIME2 updated_at
    }

    sessions {
        UUID id PK
        UUID user_id FK
        UUID auth_identity_id FK
        VARCHAR session_token_hash UK
        VARCHAR ip_address
        VARCHAR user_agent
        NVARCHAR entra_access_token
        NVARCHAR entra_refresh_token
        DATETIME2 entra_access_token_expires_at
        DATETIME2 expires_at
        DATETIME2 revoked_at
        DATETIME2 created_at
        DATETIME2 updated_at
    }

    email_verification_tokens {
        UUID id PK
        UUID identity_id FK
        VARCHAR token_hash UK
        DATETIME2 expires_at
        DATETIME2 consumed_at
        DATETIME2 created_at
    }

    password_reset_tokens {
        UUID id PK
        UUID identity_id FK
        VARCHAR token_hash UK
        DATETIME2 expires_at
        DATETIME2 consumed_at
        DATETIME2 created_at
    }

    auth_audit_logs {
        BIGINT id PK
        DATETIME2 occurred_at
        VARCHAR event_type
        UUID user_id FK
        UUID session_id FK
        VARCHAR provider
        VARCHAR client_ip
        NVARCHAR xff_raw
        VARCHAR connection_ip
        VARCHAR user_agent
        VARCHAR reason_code
        NVARCHAR metadata
    }

    async_jobs {
        UUID id PK
        VARCHAR job_type
        UUID requested_by_user_id FK
        VARCHAR status
        VARCHAR queue_name
        VARCHAR task_name
        NVARCHAR requested_payload
        NVARCHAR result_payload
        VARCHAR error_message
        INTEGER retry_count
        DATETIME2 started_at
        DATETIME2 finished_at
        DATETIME2 expires_at
        DATETIME2 created_at
        DATETIME2 updated_at
    }

    async_job_artifacts {
        UUID id PK
        UUID job_id FK
        VARCHAR artifact_type
        VARCHAR storage_provider
        VARCHAR container_name
        VARCHAR blob_path
        VARCHAR file_name
        VARCHAR content_type
        INTEGER file_size_bytes
        VARCHAR checksum
        DATETIME2 expires_at
        DATETIME2 created_at
    }

    users ||--o{ auth_identities : has
    users ||--o{ sessions : has
    auth_identities ||--o{ email_verification_tokens : issues
    auth_identities ||--o{ password_reset_tokens : issues
    users o|--o{ auth_audit_logs : actor
    sessions o|--o{ auth_audit_logs : source_session
    users ||--o{ async_jobs : requested_by
    async_jobs ||--o{ async_job_artifacts : produces
```

## Alembic 方針

- Alembic は `apps/backend/alembic/` で管理
- autogenerate は model 定義を元に実行
- schema 作成は migration に含めず、`scripts/init/sql/deploy.sh` を前提とする

## 非同期ジョブ基盤

### 基本構成

- API は job row を `core.async_jobs` に作成
- API は Service Bus へ `job_id` ベースのメッセージを送信
- worker は DB を正本として job を claim し、状態更新する
- 成果物本体は Blob Storage、メタデータは `core.async_job_artifacts`

### job_type

- `auth_audit_export`
- `sample_wait_blob`

### status

- `queued`
- `running`
- `succeeded`
- `failed`
- `canceled`
- `expired`

### 関連ファイル

- dispatcher: `app/services/jobs/async_job_dispatcher.py`
- worker runtime: `app/workers/runtime.py`
- registry: `app/workers/job_registry.py`
- audit export worker: `app/workers/jobs/audit_export.py`
- sample worker: `app/workers/jobs/sample_wait_blob.py`

## Cleanup scheduler

cleanup は `app.schedulers.scheduler_cleanup` から起動します。

対象:

- `sessions`: 期限切れセッション削除
- `audit`: 監査ログ retention cleanup
- `jobs`: 期限切れ成果物削除、stale `running` ジョブの `failed` 化

対応ファイル:

- `app/schedulers/cleanup/runners/sessions.py`
- `app/schedulers/cleanup/runners/audit_logs.py`
- `app/schedulers/cleanup/runners/async_jobs.py`

## 設定管理

設定は `app/core/settings/config.py` の `AppSettings` に集約しています。  
ローカルでは `apps/backend/.env` があれば読み込み、本番は環境変数注入前提です。

主要設定カテゴリ:

- Azure SQL: `DATABASE_URL`, `DATABASE_*`
- Auth: `SESSION_*`, `EMAIL_*`, `PASSWORD_*`, `ENTRA_*`
- Async jobs: `ASYNC_JOB_*`, `SERVICE_BUS_*`
- Storage: `AZURE_BLOB_*`
- Cleanup: `SESSION_CLEANUP_ENABLED`, `AUDIT_CLEANUP_ENABLED`, `CLEANUP_BATCH_SIZE`

## 実装上の注意

- DB の日時列は `DATETIME2(3)` を使用し、Python 側で UTC として扱います
- enum 値は DB 上は文字列で保持し、アプリケーション層の `StrEnum` は定数として使います
- JSON 的な payload / metadata は Azure SQL 上では `NVARCHAR(MAX)` として保存します
- `/backend/health` の依存性キーは `dependencies.sql` です

## 品質確認

backend 単体の確認:

```bash
make backend-format
make backend-lint
make backend-typecheck
make backend-test
```

2026-03 時点では、少なくとも `ruff` / `pyright` / `pytest` は通る状態を基準とします。
