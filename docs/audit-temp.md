# 認証セッション運用改善 設計メモ（Draft）

## 1. 背景

現行実装では、認証セッションを `sessions` テーブルで保持しており、失効（`expires_at`）や無効化（`revoked_at`）済みレコードも履歴として残るため、運用を続けるとテーブルが継続的に肥大化する。

今回の目的は以下。

- `sessions` を認証制御のための短期データに限定し、期限切れデータを自動削除する。
- 監査目的の長期保持データは別テーブルへ分離する。
- 監査ログは全認証イベントを DB 保存し、保持期間は環境変数で制御する。
- cleanup 実行基盤は AKS の Kubernetes CronJob を採用する。
- 今後の本番運用を見据え、Dockerfile / Helm チャートも作業ステップに含める。

---

## 2. 前提・制約

### 2.1 技術前提

- Backend: FastAPI + SQLAlchemy + Alembic + PostgreSQL
- 認証方式: Entra ID（OIDC） + Email/Password
- セッション管理: DB (`sessions`) + HttpOnly Cookie
- 実行環境想定: AKS

### 2.2 運用前提

- 監査ログは「全認証イベント」を保存対象とする。
- cleanup は API リクエスト経路ではなく、バッチ実行で行う。
- Helm 導入はこれからのため、チャート整備を計画に含める。

### 2.3 Entra トークン関連の注意

- Entra のトークン寿命はポリシーやクライアント種別の影響を受けるため、アプリ側で「refresh token は常に使える」とは仮定しない。
- セッション TTL は、Entra 側の実運用ポリシーより安全側（短め）に設定する。
- refresh 失敗時は再ログインへフォールバックする設計を維持する。

参考:

- https://learn.microsoft.com/ja-jp/entra/identity-platform/configurable-token-lifetimes

---

## 3. 要件整理

## 3.1 セッション運用要件

- セッション TTL は環境変数化する。
- デフォルトは 7 日。
- 期限切れ後の削除猶予は環境変数化する。
- デフォルトは 3 日。
- 削除猶予の最大は 7 日。
- 期限切れ + 猶予超過のセッションは自動削除する。

## 3.2 監査ログ要件

- 監査ログはセッション管理テーブルから分離して別テーブル化する。
- 全認証イベントを DB 保存する。
- 保持期間は環境変数化する。
- デフォルトは 12 か月（1 年）。
- 最大は 84 か月（7 年）まで設定可能にする。
- 監査ログはパーティショニングで管理する。

## 3.3 インフラ/実行要件

- cleanup 実行は Kubernetes CronJob を採用。
- API 本体とは別実行のジョブ（CLI）で cleanup を行う。
- 将来の AKS 本番運用を想定し、Dockerfile / Helm チャートに組み込む。

---

## 4. 目標アーキテクチャ

## 4.1 データ責務の分離

- `sessions`
  - 目的: 現在有効な認証セッションの制御
  - 保持: 短期（TTL + 猶予）
  - cleanup: 自動削除対象

- `auth_audit_logs`（新規）
  - 目的: 認証監査（追跡・調査・証跡）
  - 保持: 中長期（1 年〜7 年）
  - cleanup: 保持期間超過データを月単位で廃棄
  - 運用: パーティショニング

## 4.2 処理責務

- API リクエスト時
  - 認証処理実行
  - 監査イベントを `auth_audit_logs` へ追加

- CronJob 実行時
  - `sessions` cleanup
  - `auth_audit_logs` retention cleanup

---

## 5. DB 設計（案）

## 5.1 `sessions` テーブル

現行を維持しつつ、運用で以下の条件で削除:

- `expires_at < now() - interval '<grace days> day'`

補足:

- `revoked_at` は「明示失効日時」。
- `expires_at` は「自然失効日時」。
- 有効判定は基本的に `revoked_at IS NULL AND expires_at > now()`。

インデックス確認/推奨:

- `sessions(expires_at)`
- `sessions(user_id)`
- 必要なら `sessions(revoked_at)`

## 5.2 `auth_audit_logs` テーブル（新規）

想定カラム（例）:

- `id` (UUID or BIGINT)
- `occurred_at` (TIMESTAMPTZ, NOT NULL)
- `event_type` (TEXT or ENUM)
- `result` (TEXT: success/fail)
- `user_id` (UUID, NULL 可)
- `session_id` (UUID, NULL 可)
- `provider` (TEXT: entra/email)
- `client_ip` (INET or TEXT)
- `user_agent` (TEXT)
- `reason_code` (TEXT, NULL 可)
- `metadata` (JSONB)

推奨パーティション:

- 親: `PARTITION BY RANGE (occurred_at)`
- 子: 月次パーティション（例: `auth_audit_logs_2026_03`）

インデックス（親または各子）例:

- `(occurred_at)`
- `(event_type, occurred_at DESC)`
- `(user_id, occurred_at DESC)`
- 必要に応じて `(result, occurred_at DESC)`

---

## 6. 監査イベント定義（保存対象）

最低限、以下を全て保存する。

- login success
- login fail
- logout
- session revoke
- session refresh success/fail
- email signup
- email verify success/fail
- password change success/fail
- password reset request
- password reset confirm success/fail
- entra callback success/fail
- entra profile fetch success/fail（必要に応じて）

イベント記録の原則:

- 成功/失敗を統一フォーマットで保存。
- 認証失敗でも個人情報を過剰保存しない。
- `metadata` は拡張可能だが、機密情報（平文トークン、平文パスワード）は禁止。

---

## 7. 環境変数設計（案）

## 7.1 セッション関連

- `SESSION_TTL_HOURS`
  - 既定: `168`（7日）
  - 説明: アプリセッション有効期間
  - 注意: Entra 実運用ポリシーより長すぎない値を推奨

- `SESSION_EXPIRED_GRACE_DAYS`
  - 既定: `3`
  - 許容: `0..7`
  - 説明: 期限切れ後、cleanup で削除するまでの猶予日数

## 7.2 監査ログ関連

- `AUTH_AUDIT_RETENTION_MONTHS`
  - 既定: `12`
  - 許容: `1..84`（1か月..7年）
  - 説明: 監査ログ保持期間

## 7.3 cleanup 実行制御

- `SESSION_CLEANUP_ENABLED`
  - 既定: `true`

- `AUDIT_CLEANUP_ENABLED`
  - 既定: `true`

- `CLEANUP_BATCH_SIZE`
  - 既定: `5000`
  - 説明: 1 回の削除件数上限（ロック/負荷抑制）

---

## 8. Cleanup 実行方式（採用）

## 8.1 Kubernetes CronJob（AKS）

採用理由:

- API Pod と分離して実行できる。
- 失敗時の再実行、履歴、監視が Kubernetes 標準で扱いやすい。
- スケール時に二重実行制御（`concurrencyPolicy: Forbid`）が容易。

推奨設定:

- `concurrencyPolicy: Forbid`
- `restartPolicy: OnFailure`
- `backoffLimit` を適切化
- `successfulJobsHistoryLimit` / `failedJobsHistoryLimit`
- `ttlSecondsAfterFinished`
- UTC 基準スケジュールで運用

---

## 9. Docker / Helm 設計方針

## 9.1 Dockerfile

- backend API 用イメージを 1 つ作成。
- 同一イメージで以下 2 形態を実行可能にする。
  - API: `gunicorn app.main:app ...`
  - Job: `python -m app.schedulers.scheduler_cleanup ...`

意図:

- API と cleanup の実行環境差異を最小化。
- 依存パッケージ管理を一本化。

## 9.2 Helm チャート

最小構成:

- `Deployment`（API）
- `Service`
- `CronJob`（sessions cleanup）
- `CronJob`（audit retention cleanup）
- `ConfigMap` / `Secret`（環境変数注入）

`values.yaml` で管理する主項目:

- cleanup の有効/無効
- スケジュール
- バッチサイズ
- TTL / retention / grace

---

## 10. 実装ステップ（詳細）

## Phase 0: 仕様確定

目的:

1. 環境変数名・既定値・上限下限を確定する。
2. 監査イベント一覧と `event_type` 命名規約を確定する。
3. 監査ログに保存する PII 境界を確定する。
4. 実装フォルダ構成（API/Worker/Adapter/Job）を確定する。

成果物:

- 設計メモ更新
- `.env.example` 追記仕様
- フォルダ構成（新規ディレクトリ含む）確定メモ

### 0-9. エクスポート機能向けフォルダ構成（確定）

- エクスポート関連実装は以下に配置する。
  - `app/adapters/queue/`（Redis/Celery 接続と汎用 enqueue API）
  - `app/adapters/storage/`（Azure Blob I/O）
  - `app/workers/`（Celery アプリ定義 / タスク登録）
  - `app/repositories/auth/`（Export Job 永続化）
  - `app/services/auth/`（Export ユースケース / 業務別 dispatcher）
  - `app/schedulers/`（retention cleanup CLI）
- 命名方針:
  - queue: `celery_app.py`, `task_dispatcher.py`（汎用のみ）
  - storage: `azure_blob.py`
  - worker task: `audit_export_tasks.py`
  - service: `auth_audit_export_service.py`, `auth_audit_export_dispatcher.py`
  - repository: `auth_audit_export_repository.py`

### 0-10. エクスポート要件（確定 / FIX）

- 対象範囲:
  - 監査ログ画面と同一フィルタ条件を対象とする（keyword/date/event_type/provider）。
  - `from` / `to` の未指定を許可する（未指定時は全期間対象）。
- 形式:
  - 初期実装は CSV のみ。
- 件数・実行制御:
  - 1ジョブ最大件数: `50,000`。
  - 全体同時実行上限: `3`。
  - ユーザー同時実行上限: `1`。
- タイムゾーン:
  - `UTC` / `Asia/Tokyo` の2択をAPI入力で受け付ける。
  - CSV出力日時は指定タイムゾーンで整形する。
- 出力列:
  - 監査ログ画面表示列 + `xff_raw` / `connection_ip` / `user_agent` / `metadata` を含める。
  - `metadata` は JSON 文字列を1カラムで出力する。
- CSV仕様:
  - 文字コードは `UTF-8 with BOM`。
  - ファイル名は `{job_id}.csv`。
- 権限制御:
  - ジョブ作成APIはログイン済みユーザーが利用可。
  - ダウンロードはジョブ作成者本人のみ許可。
- 実行方式:
  - Redis ブローカー + Celery worker。
  - 失敗時は新規ジョブ作成で再実行する。
  - フロントの状態監視は 5 秒間隔ポーリング。
  - 進捗表示は `status`（queued/running/succeeded/failed）のみ。
  - タスク再試行は最大3回、1ジョブ実行タイムアウトは30分。
- エラーハンドリング:
  - 画面表示は汎用メッセージ、詳細はサーバーログに記録する。
- 保持/削除:
  - エクスポートファイル保持期間は既定365日、上限2555日（7年）を環境変数で制御。
  - 保持期限超過ファイルは日次バッチで削除する。

### 0-1. 環境変数仕様（確定）

- `SESSION_TTL_HOURS`
  - default: `168`（7日）
  - min: `1`（1時間）
  - max: `720`（30日）
  - 意図: 短すぎる設定ミスを防止しつつ、過度に長いセッションを防止する。

- `SESSION_EXPIRED_GRACE_DAYS`
  - default: `3`
  - min: `0`
  - max: `7`
  - 意図: 運用調査猶予を確保しつつ、セッションテーブル肥大化を抑制する。

- `AUTH_AUDIT_RETENTION_MONTHS`
  - default: `12`
  - min: `1`
  - max: `84`（7年）
  - 意図: 監査保持要件（デフォルト1年、最大7年）を満たす。

- `SESSION_CLEANUP_ENABLED`
  - default: `true`

- `AUDIT_CLEANUP_ENABLED`
  - default: `true`

- `CLEANUP_BATCH_SIZE`
  - default: `5000`
  - min: `100`
  - max: `50000`
  - 意図: 大量削除時のロック/IO負荷と実行時間のバランスを取る。

### 0-2. 監査イベント仕様（確定）

- `event_type` は `ENUM` で管理する。
- 形式は `<domain>.<action>.<result>` とする。
- `domain` は固定で `auth`。
- `action` は以下を許可する。
  - `login`
  - `logout`
  - `session_refresh`
  - `session_revoke`
  - `signup`
  - `email_verify`
  - `password_change`
  - `password_reset_request`
  - `password_reset_confirm`
  - `entra_callback`
  - `entra_profile_fetch`
- `result` は `success` / `fail`。
- 例:
  - `auth.login.success`
  - `auth.login.fail`
  - `auth.password_reset_confirm.success`
  - `auth.entra_callback.fail`
- 新イベント追加時は Alembic migration で ENUM 値を追加する。

### 0-3. 監査ログのデータ保持境界（確定）

保存してよい:

- `user_id`
- `session_id`
- `provider`（`entra` / `email`）
- `client_ip`
- `xff_raw`
- `connection_ip`
- `user_agent`
- `reason_code`
- 最小限の `metadata`

保存しない（禁止）:

- 平文パスワード
- 平文 access token / refresh token
- メール本文・本人確認トークンの平文
- Authorization ヘッダ生値
- Cookie 生値

補足:

- `email` は原則 `metadata` に保存しない（必要時のみマスクまたはハッシュ化）。

### 0-4. User 参照整合性ポリシー（確定）

- `users` テーブルは物理削除しない（論理運用）。
- ユーザー有効/無効は `users.is_active` で制御する。
- 監査ログは `user_id` 参照を維持し、表示/CSV出力時は `users` と JOIN して情報解決する。
- 監査ログ `user_id` の外部キーは `ON DELETE SET NULL` とする。
  - 現行運用では発動しない想定だが、将来の運用変更や手動削除事故時の保険として採用する。

### 0-5. クライアントIP保存仕様（確定）

- `client_ip`: 実クライアントIP（`X-Forwarded-For` 先頭値）を保存する。
- `xff_raw`: `X-Forwarded-For` ヘッダー生値を保存する。
- `connection_ip`: `request.client.host`（直近接続元）を保存する。
- 前提:
  - AppGW が `X-Forwarded-For` を付与していること。
  - 信頼できるプロキシ経路のみで本APIへ到達すること。

### 0-6. `metadata` 仕様（確定 / 4KB上限）

- `metadata` は `JSONB` とする。
- サイズ上限は `4KB` とする。
- 保存可能キーは allowlist で固定する。
  - `path`
  - `method`
  - `request_id`
  - `user_type`（`internal` / `external`）
  - `reason_detail`
  - `lockout_count`
  - `lockout_until`
  - `entra_tenant_id`
  - `entra_oid`
  - `mfa_performed`（boolean）
  - `metadata_truncated`（boolean）
- 運用ルール:
  - 上限超過時は値をトリムし、`metadata_truncated=true` を付与する。
  - allowlist 外キーは保存しない。
  - 機密情報（トークン/パスワード/Cookie/Authorization 生値）は保存禁止。

### 0-7. cleanup・保持運用仕様（確定）

- 監査ログテーブル主キーは `BIGINT` とする。
  - 理由: 高頻度INSERT前提で、`UUID` より行/インデックスが小さく、書き込み・検索効率が高い。
  - 将来外部連携が必要な場合は、主キーとは別に外部公開用識別子（UUID等）を追加する。

- retention cleanup は「月次パーティション + DROP 主体」とする。
  - パーティション粒度は月単位（`occurred_at` の RANGE partition）。
  - 保持期限を超えた月パーティションは `DROP` で廃棄する。
  - 保持は月単位で判定し、境界月の `DELETE` 補正は行わない。
  - 運用は `audit retention cleanup` ジョブに統合し、削除だけでなく将来月パーティション作成も同時に実施する。
    - 例: 実行時点で「翌月」のパーティションを `CREATE TABLE IF NOT EXISTS` で確保する。
    - これにより、月替わり時の INSERT 失敗（子パーティション不足）を防止する。

- cleanup 実行頻度は用途別に分離する。
  - `sessions cleanup`: 1時間毎
  - `audit retention cleanup`: 1日1回
  - 理由: セッション削除負荷の平準化と、日次判定による運用安定化の両立。

- cleanup 実行結果の記録先は `Application Insights` とする。
  - ジョブごとに構造化ログ（`job_name`, `status`, `deleted_count`, `duration_ms`, `error` など）を出力する。
  - 監視・分析は App Insights / Log Analytics クエリを基準とする。
  - 本フェーズでは Slack/Teams 連携は対象外とする。

### 0-8. Phase 0 完了条件（DoD）

- `.env.example` へ追記すべき項目（既定値・範囲・注意点）が仕様として定義されている。
- `AppSettings` へ追加すべき項目と境界値バリデーション仕様が定義されている。
- 監査イベント一覧と `event_type` 命名規約（ENUM 方針含む）が文書化されている。
- PII 境界（保存可/不可）が文書化されている。
- `metadata` allowlist と 4KB 制約が文書化されている。
- cleanup 運用方針（DROP 主体、頻度、App Insights 記録）が文書化されている。
- エクスポート実装向けフォルダ構成が文書化されている。
- エクスポート要件（範囲/形式/権限/保持/実行制御）が文書化されている。
- Phase 0 の未確定事項が 0 件である。

## Phase 1: DB スキーマ準備

1. `event_type` 用 ENUM 型 migration 作成（確定イベント値を初期登録）。
2. `auth_audit_logs` 親テーブル migration 作成。
3. `auth_audit_logs` に必要カラムを定義。
   - `id`（BIGINT）
   - `occurred_at`
   - `event_type`（ENUM）
   - `user_id`（FK: `ON DELETE SET NULL`）
   - `session_id`
   - `provider`
   - `client_ip`
   - `xff_raw`
   - `connection_ip`
   - `user_agent`
   - `reason_code`
   - `metadata`（JSONB）
4. 初期パーティション（月次）作成 migration。
5. インデックス作成 migration（`occurred_at`, `event_type+occurred_at`, `user_id+occurred_at` など）。
6. 既存 `sessions` インデックス見直し（不足があれば追加 migration）。
7. パーティション保守方針を反映するため、将来月の事前作成手順（またはジョブ）を設計する。

成果物:

- Alembic revision 複数本

## Phase 2: アプリケーション実装

1. 設定クラス（pydantic-settings）へ新 env を追加し、境界値バリデーションを実装する。
   - `SESSION_TTL_HOURS`（min/max）
   - `SESSION_EXPIRED_GRACE_DAYS`（0..7）
   - `AUTH_AUDIT_RETENTION_MONTHS`（1..84）
   - `SESSION_CLEANUP_ENABLED`
   - `AUDIT_CLEANUP_ENABLED`
   - `CLEANUP_BATCH_SIZE`（min/max）
   - `SESSION_TTL_SECONDS` は廃止し、参照コード・env・ドキュメントを `SESSION_TTL_HOURS` に一本化する。
2. 監査ログ Repository / Service を作成する。
   - `event_type` は ENUM 前提で保存
   - `user_id/session_id/provider/client_ip/xff_raw/connection_ip/user_agent/reason_code/metadata` を統一インタフェースで受け取る
3. `metadata` の保存制御を実装する。
   - allowlist フィルタ
   - 4KB 制限
   - 超過時 `metadata_truncated=true` 付与
4. 認証フロー各所へ監査イベント記録を追加する（success/fail 両方）。
   - login / logout / session_refresh / session_revoke
   - signup / email_verify / password_change
   - password_reset_request / password_reset_confirm
   - entra_callback / entra_profile_fetch
5. `client_ip` / `xff_raw` / `connection_ip` 解決ロジックを実装する（信頼プロキシ前提）。
   - 本番想定（AppGW→FW→AKS）:
     - `client_ip`: `X-Forwarded-For` 先頭
     - `xff_raw`: ヘッダー生値
     - `connection_ip`: `request.client.host`
   - ローカル開発/検証（AppGW/FW 経路なし）:
     - `X-Forwarded-For` が無い場合は `xff_raw=None`
     - `client_ip` と `connection_ip` は `request.client.host` を採用
     - テスト時はヘッダー有無の両ケースを必ず検証する
6. 監査ログ表示画面（参照UI）を作成する。
   - バックエンド: 監査ログ一覧取得APIを追加（ページング / 絞り込み / 並び替え）
   - フロントエンド: 監査ログ一覧画面を追加（event_type, user_id, session_id, occurred_at を中心に表示）
   - 表示ポリシー: 現時点は「ログイン済みユーザー参照可」とし、将来「システム管理者のみ参照可」へ切り替える
7. cleanup 実行モジュール（CLI）を追加する。
   - `sessions cleanup` コマンド
   - `audit retention cleanup` コマンド
8. `sessions cleanup` を実装する。
   - 条件: `expires_at` + `SESSION_EXPIRED_GRACE_DAYS` 超過
   - 実行: バッチ削除（`CLEANUP_BATCH_SIZE`）
9. `auth_audit_logs retention cleanup` を実装する。
   - 月次パーティション `DROP` 主体
   - 保持期間は月単位で判定
   - 将来月パーティション作成（翌月）を同一ジョブで実施
10. cleanup 実行結果を App Insights 向け構造化ログで出力する。
   - `job_name`
   - `status`
   - `deleted_count`
   - `duration_ms`
   - `error`

成果物:

- `app/schedulers/...` 追加
- `app/core/settings/config.py` 更新
- 認証サービス更新

### Phase 2 詳細設計: 監査ログ記録仕様（実装反映）

本節は、`auth_audit_logs` への記録仕様を「現行実装」に合わせて固定する。

#### 2-1. 基本方針

- `event_type` は `AuthAuditEventType`（ENUM）を使用する。
- `user_id` / `session_id` は「取得可能な場合のみ」保存する。
- 監査ログ記録失敗は本処理を失敗させない（ベストエフォート）。
- 監査ログの `metadata` は allowlist + 4KB 制限を適用する。

#### 2-2. IP 記録方針

- `client_ip`: `X-Forwarded-For` 先頭 IP（不在/不正時は `connection_ip`）
- `xff_raw`: `X-Forwarded-For` ヘッダー生値（空文字は `None`）
- `connection_ip`: `request.client.host`

実装:

- `app/core/network/client_ip.py::resolve_client_ips`
- `app/api/routers/auth.py::_record_auth_audit`

#### 2-3. 正常系イベントの `user_id/session_id` 記録

| event_type | user_id | session_id | 仕様 |
|---|---|---|---|
| `auth.signup.success` | あり | なし | ユーザー作成後、セッション未発行 |
| `auth.email_verify.success` | あり | なし | 検証トークン処理でユーザー確定 |
| `auth.login.success` | あり | あり | セッション発行後に再解決して記録 |
| `auth.password_change.success` | あり | あり | 現在セッションを解決して記録 |
| `auth.password_reset_request.success` | 条件付き | なし | 対象ユーザー存在時のみ `user_id` |
| `auth.password_reset_confirm.success` | あり | なし | リセット確定時に `user_id` を返却 |
| `auth.entra_callback.success` | あり | あり | Entra 認証成功後セッション発行済み |
| `auth.entra_profile_fetch.success` | あり | あり | セッション認証済みルート |
| `auth.session_revoke.success` | 条件付き | 条件付き | logout 時に有効セッション解決できた場合 |
| `auth.logout.success` | 条件付き | 条件付き | revoke と同じ解決結果を引き継ぐ |
| `auth.session_refresh.success` | あり | あり | refresh 後の新セッションを解決して記録 |

#### 2-4. 異常系イベントの `user_id/session_id` 記録

| event_type | user_id | session_id | 仕様 |
|---|---|---|---|
| `auth.signup.fail` | なし | なし | 作成前失敗（主体未確定） |
| `auth.email_verify.fail` | 条件付き | なし | 監査用ベストエフォート解決で付与可能 |
| `auth.login.fail` | なし | なし | 認証失敗時は主体を確定しない |
| `auth.password_change.fail` | あり | あり | ログイン済み + セッション解決済み |
| `auth.password_reset_confirm.fail` | 条件付き | なし | 監査用ベストエフォート解決で付与可能 |
| `auth.entra_callback.fail` | なし | なし | ユーザー/セッション確定前失敗 |
| `auth.entra_profile_fetch.fail` | あり（多く） | 条件付き | `current_session` 解決後分岐は `session_id` あり |
| `auth.session_revoke.fail` | 条件付き | 条件付き | 事前解決できた場合のみ付与 |
| `auth.session_refresh.fail` | 条件付き | 条件付き | 事前解決できた場合のみ付与 |

#### 2-5. 監査用ベストエフォート解決

失敗系でも主体特定率を上げるため、以下の監査専用ヘルパーを使用する。

- `resolve_password_reset_user_id_for_audit(token)`
  - 対象: `auth.password_reset_confirm.fail`
  - 手順: token hash -> password_reset_token -> identity -> user_id
- `resolve_email_verify_user_id_for_audit(token)`
  - 対象: `auth.email_verify.fail`
  - 手順: token hash -> email_verification_token -> identity -> user_id

運用ルール:

- いずれも「監査補助専用」であり、解決不能時は `None` を返す。
- 本来の認証成否判定・レスポンスには影響させない。

### Phase 2 補足（ローカル検証観点）

- ローカル環境では AppGW/FW を通らないため、`X-Forwarded-For` 不在が通常である。
- そのためローカル検証の期待値は「`client_ip == connection_ip`、`xff_raw is None`」を基本ケースとする。
- 併せて、明示的に `X-Forwarded-For` を付与した疑似本番ケースもテストし、先頭IP採用ロジックを確認する。

## Step 3: 監査ログエクスポート機能（Redis/Celery + Azure Blob）

### 3-0. 確定仕様（2026-02-27 更新）

- データモデルは `async_jobs` + `async_job_artifacts` の2テーブルに分離する。
- 既存 `auth_audit_export_jobs` は廃止する（データ移行なし、旧migrationは取り下げ）。
- `job_type` は `Enum` で管理し、初期値は `auth_audit_export` のみ。
- API は汎用 `/jobs` 系へ統一し、スコープは当面「自分のジョブのみ」。
- ジョブ作成は `POST /jobs`（`job_type` + `payload`）の1本に統一する。
- ダウンロードはバックエンド経由配信（SAS 直接配布はしない）。
- 同時実行制御は全 `job_type` 共通上限を適用する。
- 状態は `queued/running/succeeded/failed/canceled/expired` を採用する。
- 成果物は 1ジョブ複数件を許可する。
- `async_jobs` には `requested_payload` / `result_payload` を JSONB で保持する。
- 一覧の既定並び順は「status 優先 + created_at DESC」とする。

1. エクスポート要件を固定する。
   - 形式: CSV のみ
   - 対象: 監査ログ一覧APIと同等フィルタ（date/event_type/provider/keyword）
   - `from` / `to` 未指定可（全期間対象）
   - 上限: 1ジョブ50,000件、全体同時3、ユーザー同時1
   - 出力ファイル保持: 既定365日、上限2555日
2. データモデルを追加する（DB）。
   - `async_jobs`（ジョブ本体）
     - `id`（UUID）
     - `job_type`（Enum）
     - `requested_by_user_id`
     - `status`（queued/running/succeeded/failed/canceled/expired）
     - `requested_payload`（JSONB）
     - `result_payload`（JSONB, nullable）
     - `error_message`
     - `created_at` / `started_at` / `finished_at` / `expires_at`
   - `async_job_artifacts`（成果物）
     - `id`（UUID）
     - `job_id`（FK -> async_jobs.id）
     - `artifact_type`（Enum or String）
     - `storage_provider`（例: azure_blob）
     - `storage_path`
     - `mime_type` / `file_size_bytes` / `checksum`（必要時）
     - `created_at` / `expires_at`
   - インデックス:
     - `async_jobs`: `(requested_by_user_id, created_at DESC)`, `(status, created_at DESC)`, `(job_type, created_at DESC)`
     - `async_job_artifacts`: `(job_id, created_at DESC)`, `(expires_at)`
3. 設定値を追加する（`AppSettings` / `.env.example`）。
   - `CELERY_ENABLED`（default: true）
   - `CELERY_BROKER_URL`（Redis 接続文字列）
   - `CELERY_RESULT_BACKEND_URL`（必要時）
   - `CELERY_TASK_TIME_LIMIT_SECONDS`
   - `CELERY_AUTH_AUDIT_EXPORT_QUEUE_NAME`
   - `CELERY_AUTH_AUDIT_EXPORT_TASK_NAME`
   - `CELERY_MAX_ROWS_PER_JOB`
   - `CELERY_DEFAULT_RETENTION_DAYS`（default: 365）
   - `CELERY_RETENTION_MAX_DAYS`（上限制御）
   - `AZURE_BLOB_ACCOUNT_URL`
   - `AZURE_BLOB_CONTAINER`
   - `AZURE_BLOB_CREDENTIAL`（Storage 接続文字列を必須設定）
4. Redis/Celery アダプタを実装する。
   - `app/adapters/queue/` に実装
   - 役割:
     - Celery アプリ初期化（broker/result backend）
     - Redis 接続の共通化
     - タスク enqueue の汎用関数（業務依存なし）
     - 接続設定と再試行ポリシーの標準化
   - 業務別のタスク名/キュー名/引数整形は `app/services/auth/` の dispatcher で実装する。
5. Celery ワーカーを実装する。
   - タスク: `export_auth_audit_logs(job_id)`
   - 配置:
     - `app/workers/audit_export_tasks.py`
     - `app/workers/celery_worker.py`（Celery app 読み込み/タスク登録）
   - フロー:
     - `queued -> running`
     - フィルタに基づき監査ログをページング取得
     - CSV生成（ストリーム書き出し）
     - Azure Blob へアップロード
     - `succeeded` + メタ情報更新
     - 例外時 `failed` + `error_message`
   - 補足:
     - enqueue は `app/services/auth/auth_audit_export_dispatcher.py` 経由で行う。
     - worker 側は queue adapter の汎用 API に直接業務依存を持たない。
6. Azure Blob アダプタを実装する。
   - `upload_bytes` / `open_stream` / `delete_blob`
   - Blob パス規約:
     - `audit-exports/{yyyy}/{mm}/{job_id}.csv`
   - コンテナ規約:
     - `async-jobs` コンテナ配下に保存する（例: `async-jobs/audit-exports/...`）
7. バックエンド API を追加する。
   - `POST /backend/jobs`
     - `job_type` + `payload` でジョブ作成 + dispatcher 経由 enqueue
     - 同時実行上限（全体3/ユーザー1）を事前検証
   - `GET /backend/jobs`
     - 自分のジョブ一覧（status優先 + created_at DESC）
   - `GET /backend/jobs/{job_id}`
     - ジョブ詳細（進行状態）
   - `GET /backend/jobs/{job_id}/artifacts/{artifact_id}/download`
     - バックエンド経由で Blob からストリーム配信（直接SAS公開しない）
8. フロントエンドを実装する。
   - 監査ログ画面は `POST /jobs` で `auth_audit_export` を作成する
   - 実行中ジョブのステータス表示（queued/running/succeeded/failed/canceled/expired）
   - 完了後にダウンロードリンク表示
9. ジョブ成果物 retention cleanup を追加する。
   - 方式: 日次バッチ
   - 処理:
     - `async_job_artifacts.expires_at` 超過成果物を抽出
     - Blob を削除
     - `async_jobs` を `expired` 更新（または削除）
   - cleanup CLI にサブコマンド追加:
     - `python -m app.schedulers.scheduler_cleanup jobs`
   - 補足:
     - queue adapter は cleanup から参照しない（DB + storage adapter のみで完結）。
10. 構造化ログ/監視を追加する（App Insights）。
   - `export.job.created`
   - `export.job.started`
   - `export.job.succeeded`
   - `export.job.failed`
   - `export.cleanup.completed`
11. タスク登録方式を汎用化する。
   - `app/workers/celery_worker.py` の手動 import 依存を解消する。
   - `autodiscover_tasks` または `app/workers/tasks/__init__.py` 集約で、タスク追加時の登録漏れを防ぐ。
12. キュー/ルーティング設計を汎用化する。
   - task 名や feature 単位で queue routing を設定化する。
   - 各 dispatcher は queue 名のハードコードを避け、設定経由で解決する。
   - worker 起動時の購読キュー方針（単一/複数）を運用手順として固定する。
13. 実行制御ポリシーを共通化する。
   - 同時実行制御（global/user）、timeout、retry/backoff の標準ポリシーを定義する。
   - 各ジョブ（監査エクスポート以外を含む）は共通ポリシーを参照する実装へ寄せる。
14. ジョブ状態管理モデルを汎用化する。
   - `async_jobs` + `async_job_artifacts` を正として実装する。
   - 旧 `auth_audit_export_jobs` は撤去し、二重管理を排除する。
15. 失敗時運用と再実行導線を標準化する。
   - 失敗ジョブの再試行手順（手動/API/CLI）を定義する。
   - リトライ不能エラーの分類と運用オペレーション（調査ログ、通知）を整理する。

成果物:

- Export Job 用 migration
- Redis/Celery アダプタ
- Celery worker / task 実装
- Azure Blob アダプタ
- エクスポート API + 画面
- exports retention cleanup 実装
- 汎用ジョブ基盤化の設計・実装（登録/ルーティング/共通ポリシー/状態管理/運用手順）

## Step 4: コンテナ化

1. `apps/backend/Dockerfile` 作成。
2. API 起動コマンド確認。
3. cleanup ジョブコマンド確認（3種）。
   - `sessions cleanup`
   - `audit retention cleanup`
   - `exports retention cleanup`
4. Celery worker 起動コマンド確認。
5. コンテナ起動時の env 注入とログ出力先（App Insights 連携前提）を確認。

成果物:

- Docker build/run 手順
- API/cleanup/worker の起動コマンド定義

## Step 5: Helm 導入

1. backend chart 初期作成（`charts/backend` など）。
2. Deployment/Service を chart 化。
3. CronJob 3 種を chart 化。
   - sessions cleanup
   - audit retention cleanup
   - exports retention cleanup
4. Celery worker Deployment を chart 化。
5. `values.yaml` / `values-dev.yaml` へ cleanup/retention/export パラメータ追加。
6. 既定スケジュールを values に定義。
   - `sessions cleanup`: 1時間毎
   - `audit retention cleanup`: 1日1回
   - `exports retention cleanup`: 1日1回
7. CronJob の運用設定を values に定義。
   - `concurrencyPolicy: Forbid`
   - `backoffLimit`
   - `successfulJobsHistoryLimit` / `failedJobsHistoryLimit`
   - `ttlSecondsAfterFinished`

成果物:

- Helm チャート一式

## Step 6: 検証

1. Unit test:
   - env バリデーション
   - event_type ENUM マッピング
   - metadata allowlist/4KB 制限
   - IP 抽出ロジック（`X-Forwarded-For`）
   - retention 判定
   - cleanup 対象抽出
   - export job 状態遷移
2. Integration test:
   - セッション期限切れ削除
   - 監査ログ retention 削除
   - 認証イベント記録
   - `ON DELETE SET NULL` の整合性
   - export enqueue -> worker 実行 -> Blob 保存 -> ダウンロード
3. Staging 検証:
   - CronJob 手動実行
   - 再実行時の多重起動抑止
   - App Insights へ cleanup / export 実行ログが記録されること

成果物:

- テストケース追加
- 検証ログ

## Step 7: リリース

1. 監査ログ保存のみ先行有効化。
2. cleanup を dry-run 相当で観測（可能なら）。
3. export 機能を段階有効化（internal user 限定など）。
4. 本削除有効化（sessions/audit/exports）。
5. 運用メトリクス/アラート調整。
6. Runbook（障害時復旧、手動実行、ロールバック）を確定。

---

## 10.1 進行状況（2026-02-28 時点）

本節は、`## 10. 実装ステップ（詳細）` の現在進捗を「完了 / 進行中 / 未着手」で整理したもの。

| ステップ | 状態 | 進捗概要 |
|---|---|---|
| Phase 0: 仕様確定 | 完了 | 環境変数、監査イベント、PII境界、metadata制約、cleanup運用、エクスポート要件を確定済み。 |
| Phase 1: DB スキーマ準備 | 完了 | `auth_audit_logs`（月次パーティション）、`async_jobs`、`async_job_artifacts` を migration 適用済み。 |
| Phase 2: アプリケーション実装 | 完了 | 監査ログ記録/表示、`SESSION_TTL_HOURS` への一本化、cleanup CLI（sessions/audit/jobs）、構造化ログ出力まで実装済み。 |
| Step 3: 監査ログエクスポート機能（Redis/Celery + Azure Blob） | 完了（現スコープ） | `/jobs` API 統一、Celery 実行、Blob保存/配信、ジョブ履歴表示、jobs cleanup、汎用ジョブ基盤化を反映済み。 |
| Step 4: コンテナ化 | 未着手 | Dockerfile/起動構成の正式整備はこれから。 |
| Step 5: Helm 導入 | 未着手 | chart 化（API/CronJob/worker）はこれから。 |
| Step 6: 検証 | 進行中 | 手動検証 + CI（lint/typecheck/test）は通過。Staging でのCronJob/監視検証は未実施。 |
| Step 7: リリース | 未着手 | 段階有効化・Runbook確定はこれから。 |

### Step 3 内訳（完了確認）

- `async_jobs` / `async_job_artifacts` モデル・Repository・API を実装。
- `/backend/jobs` 系 API（作成/一覧/詳細/成果物ダウンロード）へ統一。
- Celery worker (`jobs.auth_audit_export`) と dispatcher 実装。
- Azure Blob 連携（アップロード/ダウンロード/削除）実装。
- cleanup CLI を `app.schedulers.scheduler_cleanup` に統一し、`jobs` サブコマンドを追加。
- フロント側のジョブ表示をグローバル化し、ページを跨いで状態参照可能にした。
- `make up` / `make dev` で worker 起動を含む開発導線を整備。
- backend/frontend の関連テストを追加し、CI 通過を確認済み。

### 現在の次工程

1. Step 4: Dockerfile / 実行コマンド標準化
2. Step 5: Helm（API + CronJob + Worker）実装
3. Step 6: Staging 検証（CronJob実行・App Insights監視）
4. Step 7: リリース手順・Runbook 確定

---

## 11. 運用・監視指標（推奨）

- `sessions` 総件数
- `sessions` 期限切れ件数
- 1 回の cleanup 削除件数
- `auth_audit_logs` 月次件数
- CronJob 成功/失敗回数
- cleanup 実行時間

アラート例:

- CronJob 連続失敗
- cleanup 0 件が長期継続（想定外の場合）
- sessions テーブル件数急増

---

## 12. リスクと対策

- リスク: cleanup 削除負荷で DB 負荷上昇
  - 対策: バッチ削除、低負荷時間帯実行、インデックス整備

- リスク: 監査ログ量増大
  - 対策: 月次パーティション + retention 厳守

- リスク: Entra refresh 失敗によるユーザー影響
  - 対策: 再ログイン導線整備、監査イベント記録、運用監視

- リスク: 複数 Pod で cleanup 重複実行
  - 対策: CronJob + `concurrencyPolicy: Forbid`

---

## 13. 今後の実装順（推奨）

1. 環境変数仕様確定（上限下限含む）
2. `auth_audit_logs` migration
3. 監査イベント書き込み
4. cleanup CLI 実装
5. 監査ログエクスポート（Redis/Celery + Blob）
6. Dockerfile
7. Helm chart + CronJob + Worker
8. テスト
9. README / Runbook 更新

---
