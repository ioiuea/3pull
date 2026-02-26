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
- デフォルトは 1 年（365 日）。
- 最大は 7 年（2555 日程度）まで設定可能にする。
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

- `SESSION_TTL_SECONDS`
  - 既定: `604800`（7日）
  - 説明: アプリセッション有効期間
  - 注意: Entra 実運用ポリシーより長すぎない値を推奨

- `SESSION_EXPIRED_GRACE_DAYS`
  - 既定: `3`
  - 許容: `0..7`
  - 説明: 期限切れ後、cleanup で削除するまでの猶予日数

## 7.2 監査ログ関連

- `AUTH_AUDIT_RETENTION_DAYS`
  - 既定: `365`
  - 許容: `1..2555`（約 7 年）
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
  - Job: `python -m app.jobs.auth_cleanup ...`

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

成果物:

- 設計メモ更新
- `.env.example` 追記仕様

### 0-1. 環境変数仕様（確定）

- `SESSION_TTL_SECONDS`
  - default: `604800`（7日）
  - min: `3600`（1時間）
  - max: `2592000`（30日）
  - 意図: 短すぎる設定ミスを防止しつつ、過度に長いセッションを防止する。

- `SESSION_EXPIRED_GRACE_DAYS`
  - default: `3`
  - min: `0`
  - max: `7`
  - 意図: 運用調査猶予を確保しつつ、セッションテーブル肥大化を抑制する。

- `AUTH_AUDIT_RETENTION_DAYS`
  - default: `365`
  - min: `1`
  - max: `2555`（約7年）
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
  - 保持日数境界月（例: 365日）は必要に応じて `DELETE` で補正する。

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

1. 設定クラス（pydantic-settings）へ新 env を追加しバリデーション実装。
2. 監査ログ Repository / Service 作成（ENUM、IPカラム、metadata 取扱い対応）。
3. `metadata` の allowlist フィルタと 4KB 制限（`metadata_truncated` 付与）を実装。
4. 認証フロー各所へ監査イベント記録を追加（success/fail 両方）。
5. `client_ip` / `xff_raw` / `connection_ip` 解決ロジックを実装（信頼プロキシ前提）。
6. cleanup 実行モジュール（CLI）を追加。
   - `sessions cleanup` コマンド
   - `audit retention cleanup` コマンド
7. `sessions` cleanup 実装（期限切れ + 猶予 + バッチ削除）。
8. `auth_audit_logs` retention cleanup 実装（DROP 主体 + 境界月補正 DELETE）。
9. cleanup 実行結果を App Insights 向け構造化ログで出力。

成果物:

- `app/jobs/...` 追加
- `app/core/settings/config.py` 更新
- 認証サービス更新

## Phase 3: コンテナ化

1. `apps/backend/Dockerfile` 作成。
2. API 起動コマンド確認。
3. cleanup ジョブコマンド確認（2種）。
   - `sessions cleanup`
   - `audit retention cleanup`
4. コンテナ起動時の env 注入とログ出力先（App Insights 連携前提）を確認。

成果物:

- Docker build/run 手順

## Phase 4: Helm 導入

1. backend chart 初期作成（`charts/backend` など）。
2. Deployment/Service を chart 化。
3. CronJob 2 種を chart 化。
4. `values.yaml` / `values-dev.yaml` へ cleanup/retention パラメータ追加。
5. 既定スケジュールを values に定義。
   - `sessions cleanup`: 1時間毎
   - `audit retention cleanup`: 1日1回
6. CronJob の運用設定を values に定義。
   - `concurrencyPolicy: Forbid`
   - `backoffLimit`
   - `successfulJobsHistoryLimit` / `failedJobsHistoryLimit`
   - `ttlSecondsAfterFinished`

成果物:

- Helm チャート一式

## Phase 5: 検証

1. Unit test:
   - env バリデーション
   - event_type ENUM マッピング
   - metadata allowlist/4KB 制限
   - IP 抽出ロジック（`X-Forwarded-For`）
   - retention 判定
   - cleanup 対象抽出
2. Integration test:
   - セッション期限切れ削除
   - 監査ログ retention 削除
   - 認証イベント記録
   - `ON DELETE SET NULL` の整合性
3. Staging 検証:
   - CronJob 手動実行
   - 再実行時の多重起動抑止
   - App Insights へ cleanup 実行ログが記録されること

成果物:

- テストケース追加
- 検証ログ

## Phase 6: リリース

1. 監査ログ保存のみ先行有効化。
2. cleanup を dry-run 相当で観測（可能なら）。
3. 本削除有効化。
4. 運用メトリクス/アラート調整。
5. Runbook（障害時復旧、手動実行、ロールバック）を確定。

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
5. Dockerfile
6. Helm chart + CronJob
7. テスト
8. README / Runbook 更新

---
