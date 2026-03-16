# Azure SQL 実装整理

## 1. このドキュメントの位置づけ

- 本ドキュメントは、backend / frontend をローカル開発で動かすことを優先しつつ、認証機構、非同期ジョブ、API プロテクトを `Azure SQL Database + Alembic + SQLAlchemy` 前提で再構築するための整理メモです。
- 現在の PostgreSQL 前提実装をそのまま移植するのではなく、Azure SQL 向けに設計を見直したうえで置き換える方針を前提にします。
- 旧 PostgreSQL 向けの `app/models/*` / `app/adapters/postgres/*` / `alembic/versions-bk/*` は削除済みで、現行実装は `app/adapters/sql/*` と新モデル定義を正とします。
- 本プロダクトはサービス稼働前であり、並行稼働、後方互換、既存データ移行の互換性は考慮しません。

## 2. スコープ

- 本ドキュメントの対象は以下です。
  - 認証
    - Entra ID 認証
    - Email/Password 認証
    - セッション管理
    - 認証監査ログ
  - API プロテクト
    - セッション Cookie
    - DB セッション検証
    - CSRF 対策
  - 非同期ジョブ
    - ジョブ状態管理
    - ジョブ成果物メタデータ管理
    - Azure Service Bus worker 連携
    - Azure Blob Storage 成果物保存

## 3. 目標

- `apps/backend` を Azure SQL Database 前提で起動できるようにする。
- `apps/frontend` が新しい backend API と連携して動作するようにする。
- DB 初期化は `Alembic migration` を正とする。
- ローカル開発では Azure SQL / Service Bus / Blob Storage へ実接続する。

## 3.1 現在の進捗

- 完了済み:
  - Azure SQL / pyodbc / Microsoft Entra アクセストークン前提の接続土台を追加した
  - `apps/backend/.env` と `apps/backend/.env.example` を Azure SQL 向けに更新した
  - 旧 PostgreSQL 向け `app/models-bk` を削除した
  - Azure SQL 向けの新しい `app/models/auth/*`, `app/models/jobs/*` を作成した
  - PostgreSQL 前提の旧 Alembic revision 群 `alembic/versions-bk` を削除した
  - Azure SQL 向けの初期 migration を作成し、`make alembic-upgrade` で適用した
  - Azure SQL 側へ接続し、テーブル作成済みであることを確認した
  - auth 領域の repository / service / router を `Session + app.adapters.sql.session` 前提へ切り替えた
  - `users.email_normalized` 利用と、監査ログ metadata の JSON 文字列保存に repository / service を追従させた
  - auth 領域の Python コンパイル確認を行い、構文エラーがないことを確認した
  - jobs repository / API を `Session + app.adapters.sql.session` 前提へ切り替えた
  - worker / cleanup を `app.adapters.sql.session.get_session_factory` 前提へ切り替えた
  - 監査ログ cleanup を PostgreSQL パーティション削除から、Azure SQL 向けの保持期限超過行削除へ置き換えた
  - `app.main` の import 確認を行い、backend エントリポイントの import が通ることを確認した
  - `make dev-api` と `make up-api` で backend が正常起動することを確認した
  - Email/Password ログインが成功し、Cookie セッション発行まで確認した
  - `sample_wait_blob` ジョブの API 受付、worker 実行、Blob 成果物作成、ジョブ完了まで end-to-end で確認した
  - frontend の型チェック、単体 / 結合テスト、production build が通ることを確認した
  - `users.display_name` を `NVARCHAR` 化する migration を追加し、Entra 表示名の文字化けを解消した
  - `/auth/entra/profile` での `user_type` 判定と naive / aware datetime 比較不整合を解消した
  - `auth_audit_logs.metadata` の JSON hydrate が Azure SQL 更新時に `dict` を誤送信しないよう修正した
  - `make up` 起動後の frontend E2E として、監査ログエクスポート、サインアップ、メールログイン、パスワードリセット、パスワード忘れ、Entra ログイン、Graph プロフィール取得、API プロテクト、`sample_wait_blob` を確認した
- 未完了:
  - PostgreSQL 前提の旧 adapter ファイル自体は残っているが、主要な実行導線からの参照は外れている
  - README / docs の最終整理はまだ残っている

## 3.2 現時点の起動可否

- `make alembic-upgrade` は Azure SQL へ適用済みで、DB スキーマ作成は確認済み。
- backend 単体では、`app.main` の import が通るところまで確認済み。
- backend 単体では、`make dev-api` と `make up-api` の起動確認まで完了した。
- `make up` で frontend / backend / worker を通した起動確認まで完了した。
- `make up` 上で、認証、API プロテクト、非同期ジョブ、監査ログエクスポートの主要導線を確認済み。

## 4. 確定した前提

### 4.1 DB / 接続

- DB は `Azure SQL Database` を利用する。
- 認証方式は `Microsoft Entra 認証のみ` とする。
- ローカル開発では `DefaultAzureCredential` を利用し、`az login` を前提とする。
- SQLAlchemy の接続は `pyodbc` を利用する。
- `ODBC Driver 18 for SQL Server` のインストールをローカル開発の必須前提とする。
- `DATABASE_URL` は `SQLAlchemy URL + ODBC 接続情報` を環境変数で持ち、アクセストークンはコードで注入する。
- スキーマ作成は `Alembic migration` を正とする。

### 4.2 認証 / API プロテクト

- 認証方式は以下 2 系統を維持する。
  - Entra ID: internal user
  - Email/Password: external user
- アカウント統合は `Entra 優先` とする。
- Email/Password ユーザーは `メール検証完了までログイン不可` とする。
- API 保護は、まず `認証済みかどうか` の判定を中心に実装する。
- セッションは `DB セッション + HttpOnly Cookie` で管理する。
- Cookie ベース認証の CSRF 対策は `Origin/Referer 検証` を基本とする。
- セッションは複数同時ログインを許可する。
- セッション失効は `revoked_at` を用いた論理失効とし、後段 cleanup で削除する。
- セッション有効期限は `sliding expiration` を採用する。
- Email/Password の失敗回数制御は `failed_login_count + locked_until` で管理する。

### 4.3 非同期ジョブ

- ジョブ配送は `Azure Service Bus` を利用する。
- Azure SQL は `ジョブ状態管理の正本` とする。
- 成果物本体は `Azure Blob Storage` を利用する。
- 同時実行数制御は `Azure SQL の async_jobs` を正として判定する。
- ジョブキャンセルは `queued` 状態のみ許可する。
- ジョブ再試行は `Service Bus の再配送` を使い、DB に `retry_count` を持つ。
- ジョブ保持期間は `365日` とする。
- `idempotency_key` は初期段階では持たない。
- `async_jobs.requested_by_user_id` は必須とする。
- ジョブ種別ごとの専用テーブルは初期段階では作らず、共通テーブル + JSON 文字列 payload で始める。

### 4.4 ローカル開発

- backend は `:8000`、frontend は `:3000` を標準とする。
- frontend からの backend 接続先は `VITE_BACKEND_BASE_URL` で管理する。
- ローカル開発時の Cookie は `Secure=false`, `SameSite=Lax` とする。
- backend が信頼するオリジンは `http://localhost:3000` を明示許可し、環境変数で追加可能にする。
- Email 検証 / パスワードリセットのメール送信は、ローカルでは実送信せず、開発向け応答またはログ出力を使う。
- Entra 認証はローカルでも OIDC ログインからコールバック、セッション発行まで実接続する。
- 初期データは migration と分離し、seed コマンドで投入する。
- seed には `開発用ユーザー 1 件 + 必要最小限の認証データ` を含める。

## 5. Azure SQL 向け設計方針

### 5.1 主キー方針

- `auth_audit_logs` は `BIGINT IDENTITY` を主キーとする。
- それ以外の業務テーブルは `UUID` を主キーとする。

### 5.2 日時方針

- すべて `UTC` で保存する。
- Azure SQL の日時型は `datetime2(3)` を基本とする。

### 5.3 JSON / 可変データ方針

- PostgreSQL の `JSONB` は使わず、Azure SQL では `NVARCHAR(MAX)` に JSON 文字列として保存する。
- 対象:
  - `auth_audit_logs.metadata`
  - `async_jobs.requested_payload`
  - `async_jobs.result_payload`

### 5.4 列型 / 値表現方針

- DB ネイティブ enum は使わず、`VARCHAR` + アプリ側 enum で制御する。
- 対象:
  - `auth_identities.provider`
  - `async_jobs.status`
  - `async_jobs.job_type`
  - `async_job_artifacts.artifact_type`
  - `users.user_type`

## 6. 推奨テーブル構成

### 6.1 users

- 役割:
  - アプリケーション上の利用主体
- 主な列:
  - `id`
  - `email`
  - `email_normalized`
  - `display_name`
  - `user_type`
  - `is_active`
  - `created_at`
  - `updated_at`
- 制約 / インデックス:
  - `email_normalized` 一意

### 6.2 auth_identities

- 役割:
  - 認証方式ごとの資格情報と主体識別子
- 主な列:
  - `id`
  - `user_id`
  - `provider`
  - `provider_subject`
  - `email_normalized`
  - `password_hash`
  - `failed_login_count`
  - `locked_until`
  - `email_verified_at`
  - `last_login_at`
  - `created_at`
  - `updated_at`
- 設計ルール:
  - `users` と分離する
  - `provider + provider_subject` を複合一意制約とする
  - `password_hash` は `auth_identities` に持つ
  - Email/Password の `provider_subject` は `identity UUID` を文字列化して保存する
- インデックス:
  - `user_id`
  - `email_normalized`

### 6.3 sessions

- 役割:
  - ログイン後のアプリセッション管理
- 主な列:
  - `id`
  - `user_id`
  - `auth_identity_id`
  - `session_token_hash`
  - `ip_address`
  - `user_agent`
  - `entra_access_token`
  - `entra_refresh_token`
  - `entra_access_token_expires_at`
  - `expires_at`
  - `revoked_at`
  - `created_at`
  - `updated_at`
- 設計ルール:
  - 主体は `user_id` に紐付ける
  - ログインに使った identity 追跡のため `auth_identity_id` も持つ
  - Entra トークンは暗号化して保存する
- インデックス:
  - `session_token_hash` 一意
  - `user_id`
  - `expires_at`

### 6.4 email_verification_tokens

- 役割:
  - Email/Password 認証のメール検証トークン
- 主な列:
  - `id`
  - `auth_identity_id`
  - `token_hash`
  - `expires_at`
  - `consumed_at`
  - `created_at`
- 設計ルール:
  - `auth_identity_id` に紐付ける
  - 生トークンは保存せず、ハッシュのみ保存する

### 6.5 password_reset_tokens

- 役割:
  - Email/Password 認証のパスワードリセットトークン
- 主な列:
  - `id`
  - `auth_identity_id`
  - `token_hash`
  - `expires_at`
  - `consumed_at`
  - `created_at`
- 設計ルール:
  - `auth_identity_id` に紐付ける
  - 生トークンは保存せず、ハッシュのみ保存する

### 6.6 auth_audit_logs

- 役割:
  - 認証イベントの監査証跡
- 主な列:
  - `id`
  - `occurred_at`
  - `event_type`
  - `user_id`
  - `session_id`
  - `provider`
  - `client_ip`
  - `xff_raw`
  - `connection_ip`
  - `user_agent`
  - `reason_code`
  - `metadata_json`
- 設計ルール:
  - PostgreSQL の月次パーティションは廃止する
  - Azure SQL の通常テーブル + インデックス + retention cleanup で運用する
  - `metadata_json` は `NVARCHAR(MAX)` に JSON 文字列で保持する
  - retention は `12か月`
- 初期インデックス:
  - `occurred_at`
  - `event_type + occurred_at`
  - `user_id + occurred_at`

### 6.7 async_jobs

- 役割:
  - 非同期ジョブ状態管理の正本
- 主な列:
  - `id`
  - `job_type`
  - `requested_by_user_id`
  - `status`
  - `queue_name`
  - `task_name`
  - `requested_payload_json`
  - `result_payload_json`
  - `error_message`
  - `retry_count`
  - `started_at`
  - `finished_at`
  - `expires_at`
  - `created_at`
  - `updated_at`
- 設計ルール:
  - payload は `NVARCHAR(MAX)` JSON 文字列で保持する
  - `requested_by_user_id` は必須
  - `queued` / `running` を同時実行枠消費中とみなす
  - ジョブ種別専用テーブルは初期段階では作らない
- 初期インデックス:
  - `requested_by_user_id + created_at`
  - `job_type + status + created_at`
  - `expires_at`

### 6.8 async_job_artifacts

- 役割:
  - ジョブ成果物メタデータ
- 主な列:
  - `id`
  - `job_id`
  - `artifact_type`
  - `blob_path`
  - `file_name`
  - `content_type`
  - `file_size_bytes`
  - `created_at`
- 設計ルール:
  - 成果物本体は Blob Storage に保存し、DB にはメタデータのみ持つ
  - ダウンロードは backend API 経由で認可確認して返す

## 7. backend の置き換え方針

### 7.1 ディレクトリ方針

- 現行の正本は `app/models/*` と `app/adapters/sql/*` とする。
- 旧 PostgreSQL 向け `app/adapters/postgres`、`app/models-bk`、`alembic/versions-bk` は削除済みとする。
- `alembic/env.py` は新しい SQL Base と接続実装を参照するように切り替える。

### 7.2 置き換え対象

- 接続層:
  - `app/adapters/sql/base.py`
  - `app/adapters/sql/session.py`
- ORM モデル:
  - `app/models/auth/*`
  - `app/models/jobs/*`
- repository:
  - `app/repositories/auth/*`
  - `app/repositories/jobs/*`
- API / service:
  - `app/api/routers/auth.py`
  - `app/api/routers/jobs/*`
  - `app/services/auth/*`
  - `app/services/jobs/*`
- scheduler / worker:
  - `app/schedulers/cleanup/*`
  - `app/workers/*`

### 7.3 PostgreSQL 固有実装の廃止対象

- `JSONB`
- `INET`
- PostgreSQL partition table
- `psycopg`
- PostgreSQL enum 定義
- PostgreSQL dialect UUID 型への依存
- PostgreSQL 固有 DDL / SQL への依存

## 8. frontend の方針

- `apps/frontend` は既存画面を活かし、API 契約差分に合わせて最小限修正する。
- 主な確認対象:
  - ログイン
  - サインアップ
  - パスワードリセット
  - `/auth/me`
  - 監査ログ一覧サンプル
  - 非同期ジョブ一覧 / 詳細 / 成果物取得

## 9. ローカル開発の最小構成

### 9.1 前提

- `az login` 済み
- Azure SQL の firewall で開発端末が許可済み
- `ODBC Driver 18 for SQL Server` インストール済み
- Azure SQL Database:
  - server: `sql-3pull-test`
  - database: `sql-3pull-test`

### 9.2 backend 側の設定要素

- DB 接続設定
- Entra 認証設定
- セッション Cookie 設定
- CSRF trusted origins
- Service Bus 設定
- Blob Storage 設定
- 開発用メール送信設定

### 9.3 起動確認の目標

- backend 起動
- Alembic migration 実行
- seed 実行
- frontend 起動
- Entra ログイン
- Email/Password ログイン
- 保護 API 呼び出し
- 非同期ジョブ作成
- ジョブ一覧取得

## 10. テスト方針

- 最低限、以下を自動テスト対象にする。
  - 認証サービス
  - セッション管理
  - 非同期ジョブサービス
- 単体テストだけでなく、DB 契約を含む結合テストも入れる。
- Azure 依存部分は可能な範囲でモックし、DB モデルと repository 契約を重点的に確認する。

## 11. 実装フェーズ

### Phase 1: DB 基盤の置き換え

- ステータス: 完了
- `pyproject.toml` の DB ドライバ依存を Azure SQL 前提へ置き換える
- `app/adapters/sql/base.py` と `app/adapters/sql/session.py` を追加する
- 設定クラスを Azure SQL / pyodbc / Entra トークン注入前提へ更新する
- `alembic/env.py` を差し替える

### Phase 2: 新スキーマ定義と migration 初期化

- ステータス: 完了
- 旧 PostgreSQL 向け `models-bk` / `adapters/postgres` / `versions-bk` を削除する
- 新しい `models/auth/*`, `models/jobs/*` を Azure SQL 向けに再作成する
- 初期 Alembic revision を Azure SQL 向けスキーマで作成する

### Phase 3: repository / service 置き換え

- ステータス: 完了
- 完了:
  - 認証 repository を新モデルへ置き換えた
  - 認証 service を `Session + app.adapters.sql.session` 前提へ置き換えた
  - 認証監査ログの metadata 保存を Azure SQL 向けの JSON 文字列へ寄せた
  - ジョブ repository を `Session` 前提へ置き換えた
  - `async_jobs.requested_payload` / `result_payload` の JSON 文字列保存・読出しを repository で吸収する形へ寄せた
  - jobs service 層に PostgreSQL / `AsyncSession` 依存が残っていないことを確認した

### Phase 4: API / worker / cleanup 置き換え

- ステータス: 完了
- 完了:
  - 認証 API を新 repository / service に接続し直した
  - health API の DB セッション依存を Azure SQL 側へ寄せた
  - jobs API を `Session + app.adapters.sql.session` 前提へ切り替えた
  - jobs API の payload 変換を Azure SQL の JSON 文字列読出し前提へ追従させた
  - worker を `app.adapters.sql.session.get_session_factory` 前提へ切り替えた
  - cleanup を `app.adapters.sql.session.get_session_factory` 前提へ切り替えた
  - 監査ログ cleanup を Azure SQL 向けの保持期限超過削除へ置き換えた
  - backend は `make dev-api` / `make up-api` で正常起動を確認した
  - worker / cleanup entrypoint の import が通ることを確認した

### Phase 5: ローカル実行導線と backend 動作確認

- ステータス: 完了
- 完了:
  - `.env.example` の Azure SQL 向け設定整理
  - Alembic 実行手順の整理
  - `make dev-api` / `make up-api` で backend の正常起動を確認した
  - Email/Password ログインから Cookie セッション発行まで確認した
  - `sample_wait_blob` ジョブの受付、worker 実行、Blob 成果物作成、`succeeded` 遷移まで確認した

### Phase 6: frontend 接続と E2E 確認

- ステータス: 完了
- 完了:
  - frontend の型チェックが通ることを確認した
  - frontend の unit / integration test が通ることを確認した
  - frontend の production build が通ることを確認した
  - frontend から Email/Password ログインと保護 API の動作確認を完了した
  - frontend から Email/Password サインアップとメール検証の動作確認を完了した
  - frontend からパスワード忘れ / パスワードリセットの動作確認を完了した
  - frontend から `sample_wait_blob` のジョブ作成 / 完了確認を完了した
  - frontend から Entra ログイン後のプロフィール取得が動作する状態まで修正した
  - frontend から Microsoft Graph プロフィール取得を確認した
  - frontend から `auth_audit_export` の完了確認とダウンロード導線の確認を完了した
  - `make up` の通し確認を完了した

## 12. 次の実装ステップ

次に着手する作業は以下を推奨します。

1. README / docs の最終更新を行う
2. `make up` 前提の再現手順を簡潔に整備する
3. Azure SQL 前提の残タスクを洗い出して Phase 7 以降へ分離する
4. 必要に応じて backend / frontend の E2E 手順を定型化する
5. `Makefile` の差分を確認し、不要化したターゲットや整理が必要な導線を洗い出す
6. Python ライブラリの依存を棚卸しし、不要になった package を確認する
7. 不要になったフォルダ / ファイルを確認し、削除候補を整理する
seed不要
.env.exampleの精査
- `GET /backend/health` の依存先キー名を `dependencies.sql` に揃える

## 13. 未着手だが後続で必要なもの

- Bicep / IaC 化
- 本番向けメール送信基盤
- 運用向け監査ログ詳細検索
- 実運用で必要な認可モデル
