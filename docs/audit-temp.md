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

1. 環境変数名・既定値・上限下限を確定。
2. 監査イベント一覧と `event_type` 命名規約を確定。
3. 監査ログに保存する PII の境界を確定。

成果物:

- 設計メモ更新
- `.env.example` 追記仕様

## Phase 1: DB スキーマ準備

1. `auth_audit_logs` 親テーブル migration 作成。
2. 初期パーティション（月次）作成 migration。
3. インデックス作成 migration。
4. 既存 `sessions` インデックス見直し（不足があれば追加 migration）。

成果物:

- Alembic revision 複数本

## Phase 2: アプリケーション実装

1. 監査ログ Repository / Service 作成。
2. 認証フロー各所へ監査イベント記録を追加。
3. cleanup 実行モジュール（CLI）を追加。
4. `sessions` cleanup 実装（期限切れ + 猶予 + バッチ削除）。
5. `auth_audit_logs` retention cleanup 実装（期間超過パーティション/データ削除）。
6. 設定クラス（pydantic-settings）へ新 env を追加しバリデーション実装。

成果物:

- `app/jobs/...` 追加
- `app/core/settings/config.py` 更新
- 認証サービス更新

## Phase 3: コンテナ化

1. `apps/backend/Dockerfile` 作成。
2. API 起動コマンド確認。
3. cleanup ジョブコマンド確認。

成果物:

- Docker build/run 手順

## Phase 4: Helm 導入

1. backend chart 初期作成（`charts/backend` など）。
2. Deployment/Service を chart 化。
3. CronJob 2 種を chart 化。
4. `values.yaml` / `values-dev.yaml` へ cleanup/retention パラメータ追加。

成果物:

- Helm チャート一式

## Phase 5: 検証

1. Unit test:
   - env バリデーション
   - retention 判定
   - cleanup 対象抽出
2. Integration test:
   - セッション期限切れ削除
   - 監査ログ retention 削除
   - 認証イベント記録
3. Staging 検証:
   - CronJob 手動実行
   - 再実行時の多重起動抑止

成果物:

- テストケース追加
- 検証ログ

## Phase 6: リリース

1. 監査ログ保存のみ先行有効化。
2. cleanup を dry-run 相当で観測（可能なら）。
3. 本削除有効化。
4. 運用メトリクス/アラート調整。

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

## 14. 未確定事項（次回決定）

- 監査ログテーブルの主キー方式（UUID/BIGINT）
- 監査ログでの `event_type` を ENUM にするか TEXT にするか
- retention cleanup を「パーティション DROP」主体にするか「DELETE」主体にするか
- cleanup の実行頻度（1時間毎 or 1日毎）
- cleanup 実行結果の通知先（Slack / Teams / App Insights）

