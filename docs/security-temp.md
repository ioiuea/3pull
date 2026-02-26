# Security Review Memo (Temporary)

## 対象
- Frontend: `apps/frontend`
- Backend: `apps/backend`
- 主題: XSS 対策、BFF + Cookie セッション運用における CSRF / SameSite / HttpOnly / セッション固定化対策

## 現在の評価

### 総評
- 現状は「BFF + Cookie セッション」の基本対策は実装済みで、主要な実装方針は妥当。
- 一方で、CSP などのブラウザ側の防御層が未実装であり、XSS 混入時の被害縮小余地が残る。

### 良い点（実装確認済み）
1. セッション Cookie は `HttpOnly` で発行されている。
2. `Secure` / `SameSite` が設定で制御され、既定値が `secure=true`, `samesite=lax` になっている。
3. CSRF 対策として、状態変更メソッドに対する `Origin/Referer` 検証ミドルウェアがある。
4. フロント API ヘルパーは `credentials: include` を標準化している。
5. セッショントークンは DB に生値保存せず、ハッシュ保存で運用される。
6. セッション更新時はローテーション（旧セッション失効 + 新規発行）となっている。

### 懸念点
1. CSP を含むセキュリティヘッダー防御層が不足している。
2. `dangerouslySetInnerHTML` の使用箇所があり、将来的にデータ起源が変化した場合のリスク管理が必要。

## 対策したほうがよいこと（優先順）

### 高優先
1. CSP 導入（まず `Report-Only` で導入し、違反観測後に強制化）。
2. `dangerouslySetInnerHTML` の運用ガードをチームルール化（原則禁止 + 例外許可制）。

### 中優先
1. セキュリティヘッダーの追加。
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `frame-ancestors 'none'`（必要に応じて `X-Frame-Options` も併用）
- `Permissions-Policy`
- `Strict-Transport-Security`（HTTPS 完全前提時）

### 低優先
1. CSP 違反レポート収集基盤（`report-to` / レポートエンドポイント）整備。

## 設計を FIX するために決めること
1. CSP 適用ポイントをどこに置くか。
- 配信基盤のみ
- FastAPI のみ
- 両方（二重化）
2. 導入フェーズ。
- いきなり強制
- `Report-Only` 先行
3. `script-src` 許可方針。
- `'self'` 厳格
- 必要外部ドメイン許可
4. Google Fonts 運用方針。
- 外部許可継続
- フォントをセルフホストし外部禁止
5. `connect-src` 許可先。
- `VITE_BACKEND_BASE_URL` と必要外部 API のみ
6. クリックジャッキング対策。
- `frame-ancestors 'none'`
- 埋め込み許可ドメインを定義
7. HSTS 適用可否。
- `max-age`、`includeSubDomains`、`preload` の方針
8. CSP 違反レポート収集の有無。
9. `dangerouslySetInnerHTML` ルール。
- 全面禁止
- 例外許可制
10. `chart.tsx` のデータ起源制約。
- 内部固定値のみ許可
- 外部起源を許す場合はサニタイズ必須

## 対策案（実装方式）

### 1. CSP / セキュリティヘッダー
1. フェーズ1（観測）
- `Content-Security-Policy-Report-Only` を配信レスポンスに付与。
- 主要画面導線で違反を収集。
2. フェーズ2（強制）
- `Content-Security-Policy` へ切替。
- 追加で他セキュリティヘッダーを一括適用。
3. 運用
- 新規外部サービス導入時は CSP 更新を PR チェック項目にする。

### 2. `dangerouslySetInnerHTML` ガード
1. リント方針
- 原則禁止ルールを設定。
- 例外ファイルを明示（暫定は `chart.tsx` のみ）。
2. コード側ガード
- `ChartConfig` に入力制約を定義。
- `key` や `color` の許容パターンをホワイトリスト化。
- 許容外値は描画しない（fail-close）。
3. 運用
- 例外追加時はセキュリティレビュー必須。

### 3. BFF セッション保護の強化継続
1. 現行の `HttpOnly + Secure + SameSite + CSRF` を維持。
2. `CSRF_TRUSTED_ORIGINS` の環境差分管理を厳格化。
3. 認証/セッション系の回帰テスト観点に CSRF と Cookie 属性検証を含める。

## 想定ロードマップ
1. 週次1: ポリシー草案作成と `Report-Only` 反映
2. 週次2: 違反分析・調整
3. 週次3: CSP 強制化、`dangerouslySetInnerHTML` リント運用開始
4. 週次4: レポート運用と回帰テスト整備

## 備考
- 本ドキュメントは暫定メモであり、実装前の設計整理を目的とする。
- 実装時は環境別（local/stg/prod）の CSP 差分を明示し、段階的に適用する。
