# AGENTS

## Frontend Framework

- この `apps/frontend` は **React Router フレームワーク** を採用している。  
  参照: <https://reactrouter.com/home>
- このアプリは `npx create-react-router@latest` によって `apps` 配下にインストールされています。

## Package Manager Policy

- `apps/frontend/package.json` の `scripts.preinstall` で `npx only-allow pnpm` を実行し、利用可能なパッケージマネージャを `pnpm` に制限しています。
- `apps/frontend/package.json` の `packageManager` は `pnpm@10.30.1` に設定されています。

## Build Strategy

- このアプリは **Static Export 前提** で実装しています。
- 設定ファイル `apps/frontend/react-router.config.ts` では `ssr: false` を設定しています。
- 生成物は静的配信を前提とし、`build/client` を配信対象として扱います。

## Routing Strategy

- `flatRoutes` は利用しません。
- ルート定義は `apps/frontend/app/routes.ts` で `route` / `layout` / `index` を使い、明示的に管理します。
- ルートファイルはフォルダ階層で整理し、feature 単位で配置します。
- 画面実装は `apps/frontend/app/routes/<feature名>/` 配下に配置します。
- 全ページ共通のレイアウト・リダイレクトなどのルーティング入口コンポーネントは `apps/frontend/app/routes/` 直下に配置します。
- ルーティングの最終制御は `apps/frontend/app/routes.ts` で行います。
- `apps/frontend/app/components/` は部品単位の再利用コンポーネントを格納するフォルダとして扱います。

### Why Not `flatRoutes`

- `app/routes.ts` で `route` / `layout` / `index` を明示管理することで URL 構造・レイアウト境界・feature 単位の責務分離を一貫して保てる一方、`flatRoutes` はファイル名規約依存の暗黙解決が増えて命名変更やファイル移動時に意図しないルート変更、解釈差分、レビュー時の認知負荷を招きやすいため採用しません。

## UI Design Strategy

- UI デザイン実装では `shadcn` を利用します。
- `apps/frontend/app/components/ui/*` の既存コンポーネントを優先して再利用します。
- ボタン、カード、フォーム、テーブル、ツールチップなどの基礎 UI は独自実装より `shadcn` コンポーネントを優先して利用します。
- アイコンは `lucide` を優先して利用します。
- `apps/frontend/app/app.css` はグローバルテーマ定義のため原則編集しません。
- スタイリング時に `shadcn` の該当コンポーネントが存在しない場合は `Tailwind CSS` で実装します。

## Form Validation Strategy

- フォームバリデーションは `zod` を標準として採用し、入力値の型定義・バリデーションルール・エラーメッセージキーをスキーマに集約します。
- `react-hook-form` をフォーム状態管理の標準とし、UI は `apps/frontend/app/components/ui/form.tsx` の部品を優先して構築します。
- バリデーション結果の表示は `react-hook-form` の `errors` を経由し、画面側で i18n 翻訳キーを解決して表示します。

### Implementation Policy

- スキーマはページ単位で `const schema = z.object({...})` として定義し、`type FormValues = z.infer<typeof schema>` で型を導出します。
- サブミット時は `schema.safeParse(values)` を実行し、失敗時は `form.setError` で各フィールドにエラーを反映します。
- 可能な環境では `@hookform/resolvers` の `zodResolver` を利用してもよいですが、依存バージョン差分で型不整合が出る場合は `safeParse` 実装を優先します。
- エラーメッセージは文言直書きではなく翻訳キー（例: `validation.emailInvalid`）を `zod` スキーマに持たせます。

### Usage

- 新規フォームページ追加時は、以下の順で実装します。
- 1. `zod` スキーマ定義と `z.infer` 型定義を作成する。
- 2. `useForm<FormValues>` に `defaultValues` を与えてフォームを初期化する。
- 3. `FormField` / `FormItem` / `FormMessage` を使って UI を構築する。
- 4. サブミットで `safeParse` を実行し、成功時のみ後続処理（API 呼び出し等）を実行する。
- 5. namespace 辞書（`<feature>.json`）に `validation.*` キーを追加し、日英で文言を揃える。

## TypeScript Documentation Standard

- TypeScript の記述では [TSDoc](https://tsdoc.org/) を標準ルールとして採用します。
- 処理の意図が第三者に伝わるように、関数・主要ブロックには TSDoc 形式の説明を付けます。
- ロジックを変えないリファクタでも、命名・コメント・構造化による可読性改善は積極的に行います。

## React Component Style

- `apps/frontend/app/routes/` 配下のページコンポーネントは、原則としてアロー関数コンポーネントで統一します。
- `export default function ...` より `const Component = () => ...; export default Component;` の形式を優先します。

## I18n Strategy

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

### Language Add Procedure

- 新しい言語を追加する場合は、`apps/frontend/app/lib/i18n.ts` の `SUPPORTED_LANGUAGES` に言語コードを追加します。
- 追加言語の辞書ディレクトリ `apps/frontend/public/dictionaries/<new-lng>/` を作成し、既存 namespace（`common`・各 feature 用 namespace）を同名ファイルで揃えます。
- `"/"` リダイレクト判定（Cookie / ブラウザ言語）は `SUPPORTED_LANGUAGES` を基準に動作するため、言語追加後は `/:lng` ルーティングで実際に表示確認します。

### Feature Namespace Procedure

- feature 単位で辞書を分離する場合は、namespace 名を feature 名に合わせて作成します（例: `billing` / `account-settings` / `admin-dashboard`）。
- 辞書ファイルは `apps/frontend/public/dictionaries/<lng>/<feature-namespace>.json` に配置します。
- 対象 feature のページコンポーネントでは `useTranslation("<feature-namespace>")` を利用し、feature 固有文言を `common` に混在させないようにします。
- namespace は動的に読み込まれるため、`i18n.ts` 側への namespace 追記は不要です。

## Global State Strategy

- グローバルステート管理は `zustand` を標準ライブラリとして利用します。
- ストア定義は `apps/frontend/app/store/` 配下に配置し、UI コンポーネント内で状態定義を直接持たない方針とします。
- ストアは `state` と `actions`（更新関数）を同じ hook で公開し、更新ロジックはストア側に集約します。
- グローバルで共有する必要がない一時状態（入力中のローカル UI 状態など）は `useState` を優先し、安易に zustand に昇格しません。
- 新規ストアを追加する際は、型定義（State 型・Action 型）を先に明示し、初期値を定数化して `reset` 可能な設計を推奨します。

## IdP Authentication Strategy (Entra ID + MSAL)

- IdP 認証は Microsoft Entra ID を利用し、SPA クライアントは `@azure/msal-browser` / `@azure/msal-react` を標準採用します。
- 設定値は `apps/frontend/.env` の `VITE_ENTRA_CLIENT_ID` と `VITE_ENTRA_TENANT_ID` を必須とし、`apps/frontend/.env.example` をテンプレートとして管理します。
- MSAL 設定は `apps/frontend/app/lib/auth.ts` に集約し、`redirectUri` / `postLogoutRedirectUri` / `authority` / `loginRequest` / Graph API endpoint をここで一元管理します。
- 認証対象ルートは `apps/frontend/app/routes/protected-layout.tsx` 配下に集約し、未認証時は `loginRedirect` で Entra ID ログインへ遷移させます。
- ログイン機能を実装する場合は、未認証ユーザーの遷移導線で `loginRedirect` を実行し、`redirectStartPage` を付与して認証完了後に本来アクセスしたページへ復帰できるようにします。

### OIDC PKCE Policy

- SPA の認可フローは OIDC Authorization Code Flow with PKCE を前提にします。
- PKCE（Proof Key for Code Exchange）は、認可リクエスト時に生成した一時値（code verifier / code challenge）を使い、認可コードの盗聴・再利用リスクを低減する仕組みです。
- クライアントシークレットを保持できない SPA でも安全性を高められるため、Entra ID + SPA 構成では PKCE 前提を標準とします。

### Usage

- `apps/frontend/app/root.tsx` で `MsalProvider` をアプリ全体に適用します。
- 認証必須ページは `apps/frontend/app/routes.ts` で `layout("routes/protected-layout.tsx", [...])` の配下にのみ配置します。
- Graph API 呼び出し時は `acquireTokenSilent` を優先し、`InteractionRequiredAuthError` の場合のみ `acquireTokenRedirect` にフォールバックします。
- スコープは最小権限を原則とし、現在の標準は `User.Read` です。追加時は用途を明示して最小化します。

### Storage Policy (Current Implementation)

- 現在の MSAL キャッシュは `cacheLocation: "localStorage"` を利用しています（`apps/frontend/app/lib/auth.ts`）。
- `localStorage` には主に以下が保存されます。
- `id token` / `access token` / `refresh token` のキャッシュキー
- アカウント情報（homeAccountId / tenantId など）
- 認可処理中の一時データ（state / nonce / PKCE 関連のトランザクション情報）
- i18n の言語設定は認証情報ではなく、Cookie キー `locale` に保存します（`apps/frontend/app/lib/i18n.ts`）。
- 機微情報（クライアントシークレットや独自の認証トークン）を独自に localStorage や Cookie へ保存しないことを原則とします。
