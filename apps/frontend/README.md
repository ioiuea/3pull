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
│   │   ├── layout.tsx                    # 共通レイアウト
│   │   ├── protected-layout.tsx          # 認証必須ページのガードレイアウト
│   │   ├── landing-page.tsx              # LPページ
│   │   ├── login.tsx                     # ログインページ
│   │   ├── signup.tsx                    # サインアップページ
│   │   └── password-reset.tsx            # パスワードリセットページ
│   ├── components/                       # 再利用コンポーネント層
│   │   ├── ui/                           # shadcnベース共通UI層
│   │   ├── login-form.tsx                # ログインフォーム部品
│   │   ├── signup-form.tsx               # サインアップフォーム部品
│   │   └── password-reset-form.tsx       # パスワードリセットフォーム部品
│   ├── constants/                        # 定数層
│   │   └── product.ts                    # プロダクト名など環境非依存定数
│   ├── lib/                              # 実装ヘルパー層
│   │   ├── api-helper.ts                 # backend API呼び出しヘルパー
│   │   └── i18n.ts                       # i18n初期化/言語判定
│   └── store/                            # Zustandグローバルステート層
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

## TypeScript ドキュメント方針

- TypeScript の記述では [TSDoc](https://tsdoc.org/) を標準ルールとして採用します。
- 処理の意図が第三者に伝わるように、関数・主要ブロックには TSDoc 形式の説明を付けます。
- ロジックを変えないリファクタでも、命名・コメント・構造化による可読性改善は積極的に行います。

## React コンポーネント記述方針

- `apps/frontend/app/routes/` 配下のページコンポーネントは、原則としてアロー関数コンポーネントで統一します。
- `export default function ...` より `const Component = () => ...; export default Component;` の形式を優先します。

## i18n 方針

- 国際化対応は `i18next` + `react-i18next` + `i18next-http-backend` を利用します。
- i18n の独自ライブラリ実装は `apps/frontend/app/lib/i18n.ts` に集約します。
- 対応言語は `en` / `ja` を標準とし、URL 言語セグメント `/:lng` を正とします。
- `"/"` へのアクセス時は言語判定ロジックで `"/en"` または `"/ja"` にリダイレクトします。
- 言語判定の優先順位は `locale` Cookie -> ブラウザ言語 -> fallback (`en`) とします。
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

### Entra Graph プロファイル取得時の注意

- フロントは Graph API を直接呼ばず、`GET /backend/auth/entra/profile` を利用します。
- internal ユーザーのみ呼び出し可能なため、`user_type` を見てボタン表示を制御します。
- `access_token_expires_at` は表示用情報であり、実際の更新は backend 側の refresh 処理に委譲します。

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

### CI 除外ポリシー

- `app/components/ui/**`（shadcn 生成物）は `format` / `lint` / `typecheck:ci` の対象外とします。
- `app/app.css` は `format` / `lint` の対象外とします。
- `app/lib/utils.ts` と `app/hooks/use-mobile.ts` は `format` / `lint` / `typecheck:ci` の対象外とします。
- CI で型チェック除外を有効化する場合は `typecheck` ではなく `typecheck:ci` を使用します。
