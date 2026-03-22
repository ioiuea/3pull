# Frontend

## パッケージ管理方針

- `apps/frontend/package.json` の `scripts.preinstall` で `npx only-allow pnpm` を実行し、利用可能なパッケージマネージャを `pnpm` に制限しています。
- `apps/frontend/package.json` の `packageManager` は `pnpm@10.30.1` に設定されています。

## フレームワーク方針

- この `apps/frontend` は **React Router フレームワーク** を採用している。  
  参照: <https://reactrouter.com/home>
- このアプリは `npx create-react-router` により、React Router v7 構成として `apps` 配下にインストールされています。

### フォルダ構成戦略

- `apps/frontend/app/` は「ルーティング中心 + 再利用部品分離」で構成します。
- 実装構成は以下の `tree` を基準とします。

```text
apps/frontend
├── package.json                          # Frontend依存関係・スクリプト定義
├── react-router.config.ts                # React Router設定（ssr: false など）
├── app/                                  # アプリケーション本体
│   ├── root.tsx                          # ルートドキュメント（html/body/Meta/Links）
│   ├── routes.ts                         # ルート定義の集約（layout/route/index）
│   ├── app.css                           # グローバルスタイル/テーマ変数
│   ├── routes/                           # 画面ルート層（featureページ + レイアウト）
│   │   ├── language-redirect.tsx         # ルート言語判定リダイレクト
│   │   ├── layout.tsx                    # 共通レイアウト
│   │   ├── protected-layout.tsx          # 認証必須ページのガードレイアウト
│   │   ├── landing-page.tsx              # LPページ
│   │   ├── authentication/               # 認証画面ルート
│   │   │   ├── login.tsx                 # ログインページ
│   │   │   ├── signup.tsx                # サインアップページ
│   │   │   ├── verify-email.tsx          # メール確認ページ
│   │   │   └── password-reset.tsx        # パスワードリセットページ
│   │   ├── profile-sample/               # Graphプロフィール取得サンプル
│   │   ├── zustand-sample/               # Zustandサンプル
│   │   ├── validation-sample/            # バリデーションサンプル
│   │   ├── api-protection-sample/        # 保護APIサンプル
│   │   ├── audit-log-sample/             # 監査ログサンプル
│   │   └── async-job-sample/             # 非同期ジョブサンプル
│   ├── components/                       # 再利用コンポーネント層
│   │   ├── ui/                           # shadcnベース共通UI層
│   │   ├── authentication/               # 認証画面共有コンポーネント
│   │   │   ├── login-form.tsx            # ログインフォーム部品
│   │   │   ├── password-reset-form.tsx   # パスワードリセットフォーム部品
│   │   │   ├── signup-form.tsx           # サインアップフォーム部品
│   │   │   └── verify-email-form.tsx     # メール確認フォーム部品
│   │   ├── sample-switcher/              # 共通サンプル切替UI群
│   │   └── theme-provider.tsx            # テーマプロバイダ
│   ├── constants/                        # 定数層
│   │   └── product.ts                    # プロダクト名など環境非依存定数
│   ├── hooks/                            # SWR / UI向け hook 層
│   │   ├── use-me.ts                     # 認証状態取得
│   │   ├── use-audit-logs.ts             # 監査ログ取得
│   │   ├── use-global-async-jobs.ts      # グローバル非同期ジョブ集約
│   │   └── use-mobile.ts                 # モバイル判定
│   ├── lib/                              # 実装ヘルパー層
│   │   ├── api-helper.ts                 # backend API呼び出しヘルパー
│   │   ├── async-jobs.ts                 # 非同期ジョブ共通型・判定
│   │   ├── async-job-providers.ts        # グローバル表示用provider定義
│   │   └── utils.ts                      # 汎用ユーティリティ
│   ├── store/                            # Zustandグローバルステート層
│   │   ├── boolean-sample-store.ts       # booleanサンプルストア
│   │   ├── number-sample-store.ts        # numberサンプルストア
│   │   ├── object-sample-store.ts        # objectサンプルストア
│   │   └── string-sample-store.ts        # stringサンプルストア
├── test/                                 # テストコード
│   ├── unit/                             # 単体テスト
│   ├── integration/                      # 結合テスト
│   ├── mocks/                            # MSW モック
│   └── setup.ts                          # テスト初期化
├── scripts/                              # CI補助スクリプト
│   └── typecheck-ci.mjs                  # CI向け型チェック補助
├── public/                               # 静的配信アセット層
│   └── dictionaries/                     # i18n辞書データ層
│       ├── en/                           # 英語辞書namespace群
│       └── ja/                           # 日本語辞書namespace群
└── .env(.example)                        # Frontend環境変数定義
```

- `routes/` は画面とレイアウト境界、`components/` は UI 部品、`lib/` は実装ヘルパー、`constants/` は定数を管理します。
- i18n 辞書は `public/dictionaries/<lng>/` で namespace 単位に分離し、画面実装と文言データを分離します。

## ビルド方針

- このアプリは **Static Export 前提** で実装しています。
- 設定ファイル `apps/frontend/react-router.config.ts` では `ssr: false` を設定しています。
- 生成物は静的配信を前提とし、`build/client` を配信対象として扱います。

## ルーティング方針

- `flatRoutes` は利用しません。
- ルート定義は `apps/frontend/app/routes.ts` で `route` / `layout` / `index` を使い、明示的に管理します。
- ルートファイルはフォルダ階層で整理し、feature 単位で配置します。
- 画面実装は `apps/frontend/app/routes/<feature名>/` 配下に配置します。
- 全ページ共通のレイアウト・リダイレクトなどのルーティング入口コンポーネントは `apps/frontend/app/routes/` 直下に配置します。
- ルーティングの最終制御は `apps/frontend/app/routes.ts` で行います。
- `apps/frontend/app/components/` は部品単位の再利用コンポーネントを格納するフォルダとして扱います。

### `flatRoutes` を使わない理由

- `app/routes.ts` で `route` / `layout` / `index` を明示管理することで URL 構造・レイアウト境界・feature 単位の責務分離を一貫して保てる一方、`flatRoutes` はファイル名規約依存の暗黙解決が増えて命名変更やファイル移動時に意図しないルート変更、解釈差分、レビュー時の認知負荷を招きやすいため採用しません。

## UI 設計方針

- UI デザイン実装では `shadcn` を利用します。
- `apps/frontend/app/components/ui/*` の既存コンポーネントを優先して再利用します。
- ボタン、カード、フォーム、テーブル、ツールチップなどの基礎 UI は独自実装より `shadcn` コンポーネントを優先して利用します。
- アイコンは `lucide` を優先して利用します。
- `apps/frontend/app/app.css` はグローバルテーマ定義のため原則編集しません。
- スタイリング時に `shadcn` の該当コンポーネントが存在しない場合は `Tailwind CSS` で実装します。

## React コンポーネント記述方針

- `apps/frontend/app/routes/` 配下のページコンポーネントは、原則としてアロー関数コンポーネントで統一します。
- `export default function ...` より `const Component = () => ...; export default Component;` の形式を優先します。

## TypeScript ドキュメント方針

- TypeScript の記述では [TSDoc](https://tsdoc.org/) を標準ルールとして採用します。
- 処理の意図が第三者に伝わるように、関数・主要ブロックには TSDoc 形式の説明を付けます。
- ロジックを変えないリファクタでも、命名・コメント・構造化による可読性改善は積極的に行います。

## i18n 方針

- 国際化対応は `i18next` + `react-i18next` + `i18next-http-backend` を利用します。
- i18n の独自ライブラリ実装は `apps/frontend/app/lib/i18n.ts` に集約します。
- 対応言語は `en` / `ja` を標準とし、URL 言語セグメント `/:lng` を正とします。
- `"/"` へのアクセス時は言語判定ロジックで `"/en"` または `"/ja"` にリダイレクトします。
- 言語判定の優先順位は `locale` Cookie -> ブラウザ言語 -> fallback (`ja`) とします。
- 選択言語は Cookie キー `locale` に保存します。
- 翻訳辞書は `apps/frontend/public/dictionaries/<lng>/<namespace>.json` に配置します。
- namespace は共通文言用 `common` と、ページ単位の専用 namespace（例: LP 用 `landing`）を使い分けます。
- i18next 初期化時の namespace は `common` のみを指定し、ページ専用 namespace は `useTranslation("<namespace>")` の呼び出し時に動的ロードします。
- 新規ページを追加する際は、ページ専用 namespace の追加可否を検討し、共通化できる文言のみ `common` に置きます。

### 言語追加手順

- 新しい言語を追加する場合は、`apps/frontend/app/lib/i18n.ts` の `SUPPORTED_LANGUAGES` に言語コードを追加します。
- 追加言語の辞書ディレクトリ `apps/frontend/public/dictionaries/<new-lng>/` を作成し、既存 namespace（`common`・各 feature 用 namespace）を同名ファイルで揃えます。
- `"/"` リダイレクト判定（Cookie / ブラウザ言語）は `SUPPORTED_LANGUAGES` を基準に動作するため、言語追加後は `/:lng` ルーティングで実際に表示確認します。

### feature Namespace 運用手順

- feature 単位で辞書を分離する場合は、namespace 名を feature 名に合わせて作成します（例: `billing` / `account-settings` / `admin-dashboard`）。
- 辞書ファイルは `apps/frontend/public/dictionaries/<lng>/<feature-namespace>.json` に配置します。
- 対象 feature のページコンポーネントでは `useTranslation("<feature-namespace>")` を利用し、feature 固有文言を `common` に混在させないようにします。
- namespace は動的に読み込まれるため、`i18n.ts` 側への namespace 追記は不要です。

## グローバルステート方針

- グローバルステート管理は `zustand` を標準ライブラリとして利用します。
- ストア定義は `apps/frontend/app/store/` 配下に配置し、UI コンポーネント内で状態定義を直接持たない方針とします。
- ストアは `state` と `actions`（更新関数）を同じ hook で公開し、更新ロジックはストア側に集約します。
- グローバルで共有する必要がない一時状態（入力中のローカル UI 状態など）は `useState` を優先し、安易に zustand に昇格しません。
- 新規ストアを追加する際は、型定義（State 型・Action 型）を先に明示し、初期値を定数化して `reset` 可能な設計を推奨します。

## フォームバリデーション方針

- フォームバリデーションは `zod` を標準として採用し、入力値の型定義・バリデーションルール・エラーメッセージキーをスキーマに集約します。
- `react-hook-form` をフォーム状態管理の標準とし、UI は `apps/frontend/app/components/ui/form.tsx` の部品を優先して構築します。
- バリデーション結果の表示は `react-hook-form` の `errors` を経由し、画面側で i18n 翻訳キーを解決して表示します。

### 実装方針

- スキーマはページ単位で `const schema = z.object({...})` として定義し、`type FormValues = z.infer<typeof schema>` で型を導出します。
- サブミット時は `schema.safeParse(values)` を実行し、失敗時は `form.setError` で各フィールドにエラーを反映します。
- 可能な環境では `@hookform/resolvers` の `zodResolver` を利用してもよいですが、依存バージョン差分で型不整合が出る場合は `safeParse` 実装を優先します。
- エラーメッセージは文言直書きではなく翻訳キー（例: `validation.emailInvalid`）を `zod` スキーマに持たせます。

### 利用方法

- 新規フォームページ追加時は、以下の順で実装します。
- 1. `zod` スキーマ定義と `z.infer` 型定義を作成する。
- 2. `useForm<FormValues>` に `defaultValues` を与えてフォームを初期化する。
- 3. `FormField` / `FormItem` / `FormMessage` を使って UI を構築する。
- 4. サブミットで `safeParse` を実行し、成功時のみ後続処理（API 呼び出し等）を実行する。
- 5. namespace 辞書（`<feature>.json`）に `validation.*` キーを追加し、日英で文言を揃える。

## フェッチ戦略（SWR + api-helper）

- Fetch の実体（`fetch` 呼び出し）は `apps/frontend/app/lib/api-helper.ts` に集約します。
- キャッシュ・再検証は呼び出し側（React）で `SWR` を使って制御します。
- 方針:
- `api-helper`: transport と API 単位クライアント（`backendFetch`, `getMe`, `getAuditLogs`）
- `hooks`: SWR key 設計、再検証戦略、UI 向けデータ整形
- `components/routes`: hook を呼んで表示とイベント処理に専念する

### 実装ルール

- SWR key にはページング/検索条件を必ず含め、条件単位でキャッシュを分離します。
- 認証付き呼び出しは `backendFetch` 経由で `credentials: "include"` を維持します。
- `revalidateOnFocus` の使い分け:
- 頻繁な自動再読込が不要な画面（管理画面・一覧・検索結果）は `false` を推奨。
- 常に最新性を優先したい画面（通知件数など）は `true` を検討。
- `keepPreviousData` の使い分け:
- ページングやフィルタ変更時に表示のちらつきを抑えたい場合は `true` を推奨。
- 常に条件変更ごとに完全ローディング状態を見せたい場合は `false` でもよい。

### 記述例（推奨）

```ts
// 1) api-helper: fetch の実体
// apps/frontend/app/lib/api-helper.ts
export const getMe = async () => {
  // backendFetch は同ファイル内の共通ラッパー。
  // `VITE_BACKEND_BASE_URL + /backend` を自動付与し、
  // `credentials: "include"` とヘッダー正規化を統一する。
  const response = await backendFetch('/auth/me');
  // /auth/me は「未ログイン」を通常状態として扱うため、401 は null を返す。
  if (response.status === 401) return null;
  // 401 以外の失敗は例外として呼び出し側へ通知する。
  if (!response.ok) throw new Error(`/auth/me failed: ${response.status}`);
  // 成功時は AuthMe として返す。
  return (await response.json()) as AuthMe;
};
```

```ts
// 2) hook: SWR でキャッシュ/再検証を制御
// apps/frontend/app/hooks/use-me.ts
import useSWR from 'swr';
import { getMe } from '~/lib/api-helper';

export const useMe = () =>
  useSWR('auth-me', getMe, {
    revalidateOnFocus: false,
  });
```

```tsx
// 3) component/route: hook を使って表示とイベントを実装
import { useMe } from '~/hooks/use-me';

const { data, error, isLoading, mutate } = useMe();
if (isLoading) return <Loading />;
if (error) return <ErrorView />;
if (!data) return <LoginLink />;
return <Profile me={data} onReload={() => void mutate()} />;
```

### エラー取り扱い

- 一般ルール:
- 「未ログイン」を通常状態として扱いたい API（例: `getMe`）は `401` を `null` で返す。
- それ以外の API は `!ok` を `Error` として throw し、UI 側で `error` を表示する。
- UI 側の基本対応:
- `isLoading`: ローディング表示
- `error`: 失敗メッセージ + 再試行ボタン（`mutate`）
- `data` なし（`null`）: 未ログイン導線や空状態を表示

## 認証方針（FastAPI Session + Entra ID / Email）

- 認証の主体はバックエンド（FastAPI）とし、フロントエンドは `backend/auth/*` API を呼び出します。
- サインイン方法は Entra ID（OIDC）と Email/Password の 2 系統を提供します。
- セッションは DB（`sessions` テーブル）で管理し、フロントエンドは HttpOnly Cookie を利用します。
- 認証必須ページは `apps/frontend/app/routes.ts` で `layout("routes/protected-layout.tsx", [...])` 配下に集約します。
- 未認証時は `protected-layout` で `/backend/auth/me` を確認し、`/:lng/login` へリダイレクトします。

### 利用方法

- Entra ログインは `GET /backend/auth/entra/login` へ遷移し、コールバック後に指定した `return_to` へ復帰します。
- Email ログインは `POST /backend/auth/email/login` を利用します。
- サインアウトは `POST /backend/auth/logout` を利用します。
- 認証済みユーザー情報は `GET /backend/auth/me` で取得します。

### ストレージ方針（現行実装）

- フロントエンドで認証トークンを `localStorage` に保持しません。
- 認証セッションは HttpOnly Cookie により送信され、JavaScript から直接参照しない前提です。
- i18n の言語設定のみ Cookie キー `locale` に保存します（`apps/frontend/app/lib/i18n.ts`）。

## APIプロテクト実装で意識すること

- 保護API呼び出しは必ず `credentials: "include"` を付与します。
- このプロジェクトでは `apps/frontend/app/lib/api-helper.ts` の `backendFetch` を利用すると、Cookie 付き呼び出しを統一できます。
- `fetch` を直接使う場合は `credentials` の付け忘れに注意してください（付け忘れると未認証扱いになりやすい）。

### 認証状態の判定

- ログイン状態の判定は `GET /backend/auth/me` を正とします。
- `401` は未認証として扱い、`/:lng/login` へ遷移します。
- `403` は認可不足（ログイン済みだが権限不足）のため、未認証とは分けて扱います。

### 画面実装の基本パターン

- 認証必須ページは `protected-layout` 配下に置く。
- ページ初期化で `getMe()`（または `backendFetch('/auth/me')`）を実行し、未認証時はログインへ戻す。
- 保護APIの失敗時は以下を区別する。
- `401`: 再ログイン導線
- `403`: 権限不足メッセージ
- `5xx`: 一時障害メッセージと再試行導線

## ブラウザセキュリティの現状

- BFF + Cookie セッション前提で、frontend は認証トークンを保持せず Cookie 送信のみを担当します。
- 認証付き API 呼び出しは `backendFetch` に集約し、`credentials: "include"` を標準化しています。
- 現在のルートドキュメントでは Google Fonts を外部参照しています。将来 CSP を強制導入する場合は、この許可方針を見直します。
- `apps/frontend/app/components/ui/chart.tsx` では `<style>` タグ生成のために `dangerouslySetInnerHTML` を使用しています。現状は既存 UI 部品の利用に留め、外部起源データをそのまま流し込まない前提です。

### Entra Graph プロファイル取得時の注意

- フロントは Graph API を直接呼ばず、`GET /backend/auth/entra/profile` を利用します。
- internal ユーザーのみ呼び出し可能なため、`user_type` を見てボタン表示を制御します。
- `access_token_expires_at` は表示用情報であり、実際の更新は backend 側の refresh 処理に委譲します。

## 非同期ジョブUI実装方針

- ジョブ作成/一覧/詳細/成果物ダウンロードの API 呼び出しは `apps/frontend/app/lib/api-helper.ts` に集約します。
- グローバルジョブ状態の取得は `apps/frontend/app/hooks/use-global-async-jobs.ts` を標準利用します。
- グローバルジョブ状態は `refreshInterval: 5000`（5秒）でポーリングし、ページ間で同一 key（`global-async-jobs`）を共有します。

### 実装構成

- `apps/frontend/app/lib/async-jobs.ts`
- グローバルジョブ表示の共通型（`GlobalAsyncJobItem`, `GlobalAsyncJobProvider`）と状態判定を定義します。
- `apps/frontend/app/lib/async-job-providers.ts`
- ジョブ種別ごとの取得関数を `GlobalAsyncJobProvider[]` として登録します。
- `apps/frontend/app/hooks/use-global-async-jobs.ts`
- すべての provider をまとめて取得し、作成時刻降順で統一して返します。
- `apps/frontend/app/components/sample-switcher/async-job-switcher.tsx`
- グローバルジョブ状態の表示コンポーネント。ポップオーバーで履歴表示し、完了トーストを出します。

### 新規ジョブを追加する手順（フロント）

- 1. `api-helper.ts` にジョブ専用 API を追加する
- 作成API、一覧API、必要なら詳細/ダウンロードAPIを追加します。
- 2. 取得結果を `GlobalAsyncJobItem` へ変換する provider を作る
- `apps/frontend/app/lib/async-job-providers.ts` に `source` 固有の `fetchJobs` を追加します。
- 3. `GLOBAL_ASYNC_JOB_PROVIDERS` に登録する
- 追加後は `useGlobalAsyncJobs` のポーリング結果に自動で統合されます。
- 4. 個別ページでは必要に応じて `useSWR` を併用する
- 画面固有の表示項目（例: 独自メタデータ）は個別フック/個別 `useSWR` で取得し、グローバル状態は再利用します。

## CI 方針

- Frontend の CI は `Makefile` 経由で実行することを基本方針とします。
- CI 実行の標準入口は `make frontend-ci` とし、個別コマンド直叩きではなくターゲット経由で統一します。
- CI の実行順序は `format` -> `lint` -> `typecheck` -> `test` とします。
- 依存インストールは `make frontend-install`（`pnpm install --frozen-lockfile`）を利用し、lockfile を固定します。

### 品質ゲートルール

- `format` は `prettier --check` を利用し、未整形ファイルが1つでもあれば失敗とします。
- `lint` は `--max-warnings=0` を適用し、warning も失敗条件として扱います。
- `test` は `vitest run --passWithNoTests` を利用します。
- テストコードは `apps/frontend/test` 配下に配置し、`unit` / `integration` / `mocks` で管理します。

### テストコード記述ルール

- 各テストケース（`it` / `test`）には、以下3点が分かるコメントを必ず記載します。
- `目的`: 何の仕様を守るテストか
- `条件`: どの入力・モック・状態で実行するか
- `期待値`: 何をもって成功とするか
- コメントは「処理手順」より「仕様意図」を優先して記述します。
- 期待値は具体的なレスポンス、状態値、表示、呼び出し先などで明示します。
- 仕様変更時はテストコードとコメントをセットで更新します。

### CI 除外ポリシー

- `app/components/ui/**`（shadcn 生成物）は `format` / `lint` / `typecheck:ci` の対象外とします。
- `app/app.css` は `format` / `lint` の対象外とします。
- `app/lib/utils.ts` と `app/hooks/use-mobile.ts` は `format` / `lint` / `typecheck:ci` の対象外とします。
- CI で型チェック除外を有効化する場合は `typecheck` ではなく `typecheck:ci` を使用します。
